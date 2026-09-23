# Notebook 1 — Agents, LangChain, LangGraph, Deep Agents, and MCP

An original tutor-led workbook. Read offline; no outside reading is required. Official links support version-sensitive statements, not homework assignments. Core labs need Python; framework labs additionally need the recorded dependencies. Provider-backed examples are opt-in and are not claimed to have been run against a paid model.

## 1. Your first mental picture

Imagine a school librarian. A language model proposes what to say or do. Tools can search the catalog or calculate a fee. The harness is the surrounding program that checks requests, keeps state, executes allowed tools, and decides when to stop. An agent is the resulting action-selecting system. A capable model without that surrounding machinery is not a reliable autonomous service.

An architecture describes the parts and their connections. An algorithm describes a procedure. A framework supplies reusable machinery. A protocol defines how separate programs communicate. LangChain is framework machinery; LangGraph supplies stateful orchestration; MCP is a communication protocol. None of these names means the system has authority to perform every action a user mentions.

```text
User -> authenticated application -> agent harness -> model
                                    |    ^
                               allowed   tool result
                                tools ----+
                                    |
                               business services
```

**Example:** “Find two books about planets” may require catalog search. “Reserve a book” additionally requires the actual user's identity, a valid book, and a business-rule check. The model proposes; the application authorizes and executes.

**Check:** Is an LLM's tool-call JSON the tool execution? **Answer:** No. It is a structured request that software must validate and dispatch.

## 2. Vocabulary without mystery

A message has a role and content. State is the current record of facts needed to continue. A node is a processing step. An edge describes which step follows. A checkpoint saves progress. A reducer combines multiple updates to a state field. A thread identifies one persisted conversation or workflow history; it is not necessarily an operating-system thread.

A tool schema describes accepted arguments. A context window is how much input/output context a model can process under its limits. Memory is a system for retaining selected information beyond one call. A budget caps steps, tokens, time, money, or other resources. A trace records what happened. Orchestration coordinates dependencies, routing, retries, and results.

**Small example:** state={question, evidence, answer, step_count}. A search node adds evidence. A writing node adds an answer. A verifier checks whether evidence supports it. If evidence is missing, routing can request clarification rather than fabricate.

## 3. Agent types and how each works

These are useful categories, not one universal taxonomy. Classical AI categories and LLM workflow patterns describe different aspects and can overlap.

| Type | Child-sized example | Procedure | Main limitation |
|---|---|---|---|
| Simple reflex | Turn on a lamp if dark | Match current observation to a rule | Ignores hidden history |
| Model-based reflex | Remember whether a room was cleaned | Update internal state, then apply rules | Internal model can be wrong |
| Goal-based | Find a path to the library | Search actions toward a goal | Search can be expensive |
| Utility-based | Pick a route balancing time and tolls | Maximize a defined preference score | Bad utility gives bad behavior |
| Learning agent | Improve route estimates from trips | Update predictions or policy from feedback | Feedback may be biased |
| Tool-calling LLM agent | Look up a book, then answer | Model proposes tool, harness executes, model continues | Invalid or repeated calls |
| ReAct-style loop | Alternate information gathering and action | Observe, choose an action, inspect result | Loops or unreliable explanations |
| Plan-and-execute | Make a study plan, complete subtasks | Plan, execute steps, replan if necessary | Plans become stale |
| Router | Send arithmetic to calculator, policy to retrieval | Classify need, select specialist | Misrouting |
| Supervisor | Assign work to subject tutors | Delegate, collect, verify, synthesize | Coordination overhead |
| Evaluator-optimizer | Draft an answer, critique, revise | Generate, score, improve within a cap | Self-critique may repeat errors |
| Human-assisted | Propose a reservation for review | Pause with exact action, validate response, resume | Poor approval context |

### Lab: deterministic representatives

This offline simulation makes the decision rules visible. It does not contain a trained model or simulate actual intelligence.

```python
# lab: agent_types
def reflex(dark):
    return "lamp on" if dark else "lamp off"

def remember_and_act(previous_clean, observed_dirt):
    clean = previous_clean and not observed_dirt
    return "rest" if clean else "clean room"

def utility_route(routes):
    return min(routes, key=lambda r: r["minutes"] + 2*r["toll"])["name"]

def route_question(question):
    return "calculator" if question.startswith("add ") else "catalog"

assert reflex(True) == "lamp on"
assert remember_and_act(True, True) == "clean room"
assert utility_route([{"name":"A","minutes":10,"toll":4},
                      {"name":"B","minutes":14,"toll":0}]) == "B"
assert route_question("add 2 3") == "calculator"
print("Four agent decision rules passed")
```

`if` picks a branch. The memory rule combines the previous belief with a new observation. The utility rule assigns toll a weight of two minutes per unit, then chooses the minimum cost. The router intentionally uses a narrow rule so you can predict its behavior; a learned router would need error evaluation.

**Exercise:** Increase toll weight to zero. **Answer:** Route A wins because only travel minutes remain. Changing the objective changes behavior even with identical observations.

### Lab: goals, learning, plans, and bounded revision

These small deterministic examples expose each procedure. The running-average learner genuinely updates an estimate from observations, but it is not a neural model. The planner and reviewer are explicit rules, not an LLM.

```python
# lab: agent_goal_learning_plan
from collections import deque

def goal_agent(graph, start, goal):
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        place, route = queue.popleft()
        if place == goal:
            return route
        for neighbor in graph.get(place, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, route + [neighbor]))
    return None

def learn_reward(rewards):
    mean = 0.0
    for count, reward in enumerate(rewards, 1):
        mean += (reward - mean) / count
    return mean

def plan_and_execute(topic):
    plan = ["define", "example", "check"]
    handlers = {"define": lambda: f"Define {topic}",
                "example": lambda: f"Show a small {topic} example",
                "check": lambda: "Ask the learner to explain it"}
    return [handlers[step]() for step in plan]

def revise_until_clear(draft, max_rounds=2):
    for _ in range(max_rounds):
        if "Example:" in draft:
            return draft
        draft += " Example: two plus three equals five."
    raise RuntimeError("review budget exhausted")

assert goal_agent({"home":["road"], "road":["library"]},
                  "home", "library") == ["home","road","library"]
assert learn_reward([2,4,6]) == 4.0
assert len(plan_and_execute("gradients")) == 3
assert "Example:" in revise_until_clear("Explain addition.")
print("Goal search, estimate learning, plan execution, and revision verified")
```

Goal search uses a queue and remembers visited places. Reward learning moves the estimate by the new error divided by observation count, giving the arithmetic mean. The plan lists dependencies in a fixed order. The revision loop has a transparent acceptance rule and a cap. Real evaluators must check correctness rather than merely the presence of the word Example. Supervisor and human-assisted patterns appear in the parallel and interrupt labs below.

## 4. Build a small agent harness from scratch

The harness needs more than a loop: a tool allowlist, input validation, a budget, error handling, and a termination condition. Production also needs caller authorization, durable state, timeouts, audit records, and side-effect protections. The following toy demonstrates the central loop without network access.

```python
# lab: bounded_harness
def add(a: int, b: int) -> int:
    if type(a) is not int or type(b) is not int:
        raise ValueError("integer arguments required")
    return a + b

def run_scripted_agent(decisions, allowed_tools, max_steps=3):
    observations = []
    for step, decision in enumerate(decisions, start=1):
        if step > max_steps:
            raise RuntimeError("step budget exceeded")
        if decision["kind"] == "finish":
            return {"answer": decision["answer"], "observations": observations}
        if decision["kind"] != "tool":
            raise ValueError("unknown decision kind")
        name = decision["name"]
        if name not in allowed_tools:
            raise PermissionError("tool not allowed")
        result = allowed_tools[name](**decision["arguments"])
        observations.append({"tool": name, "result": result})
    raise RuntimeError("agent did not finish")

decisions = [
    {"kind":"tool", "name":"add", "arguments":{"a":2,"b":3}},
    {"kind":"finish", "answer":"The sum is 5."},
]
result = run_scripted_agent(decisions, {"add":add})
assert result["observations"][0]["result"] == 5
print(result["answer"])
```

`enumerate` counts decisions. The step limit prevents endless execution. A finish decision returns a result. The allowlist blocks arbitrary function names. `**arguments` unpacks named inputs into the function. The toy script supplies a final answer directly, so it does not verify that the answer used the tool result. A real harness should evaluate this and replace scripted decisions with model outputs; authorization must come from trusted application state.

**Failure drill:** Change the tool name to delete_everything. **Expected result:** PermissionError, before any such operation executes.

## 5. LangChain: reusable agent components

LangChain's current Python API exposes `create_agent` for model/tool loops with configurable middleware. Its agent implementation builds on LangGraph. The broad benefit is reusable interfaces; it does not remove the need to validate tools and evaluate results. [Official overview](https://docs.langchain.com/oss/python/langchain/overview).

Think of a toy construction kit: message objects, model adapters, tools, and structured outputs fit together. Middleware can inspect or modify processing around model and tool calls. Keep business policy in normal tested functions instead of scattering it across prompts.

### Integration recipe: supply your own configured model

This recipe is not an offline lab. It needs LangChain and a configured tool-capable chat model. `configured_model` must be supplied by your application; it is not a hidden free service.

```python recipe
from langchain.agents import create_agent

def stock_count(item: str) -> int:
    """Return the local demonstration stock count for one item."""
    return {"notebook": 7, "pencil": 12}.get(item.lower(), 0)

def build_stock_agent(configured_model):
    return create_agent(
        model=configured_model,
        tools=[stock_count],
        system_prompt="Use stock_count for counts. Do not invent stock.",
    )

# agent = build_stock_agent(configured_model)
# result = agent.invoke({"messages":[{"role":"user",
#                                    "content":"How many pencils remain?"}]})
```

The import selects the factory. The tool's type hints describe inputs and output; its docstring explains purpose. The factory composes the model, tool, and instruction. `invoke` submits the initial state. Actual tool choices and final wording depend on the model, so the guaranteed value 12 belongs to the tool, not to any untested model response.

**Check:** Should a tool return fake live inventory? **Answer:** No. This one explicitly says demonstration stock; a deployed tool must use real authorized data or disclose staleness.

### Lab: actual LangChain execution with a scripted model

This tests framework wiring and a tool round trip without a model account. The model is deliberately scripted: it asks for pencil stock once and then reports the tool message. Passing this test does not demonstrate a real model's reasoning ability.

```python
# lab: langchain_scripted_model
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

class ScriptedStockModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "teaching-scripted-stock"
    def bind_tools(self, tools, **kwargs):
        return self
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if isinstance(messages[-1], ToolMessage):
            reply = AIMessage(content="Stock result: " + messages[-1].content)
        else:
            reply = AIMessage(content="", tool_calls=[{
                "name":"stock_count", "args":{"item":"pencil"},
                "id":"stock-call-1", "type":"tool_call"}])
        return ChatResult(generations=[ChatGeneration(message=reply)])

def stock_count(item: str) -> int:
    """Return demonstration stock for a named item."""
    return {"pencil":12, "notebook":7}.get(item.lower(), 0)

stock_agent = create_agent(model=ScriptedStockModel(), tools=[stock_count])
stock_result = stock_agent.invoke({"messages":[{"role":"user","content":"Pencil stock?"}]})
assert stock_result["messages"][-1].content == "Stock result: 12"
assert any(isinstance(message, ToolMessage) for message in stock_result["messages"])
print("LangChain invoked the tool and supplied its result to the scripted model")
```

The subclass supplies the model interface. `bind_tools` is a no-op only because this fake already knows its sole test action. `_generate` inspects the last message: a tool result means finish; otherwise emit a structured tool request. The framework performs dispatch and appends the tool result. Returning ChatResult and ChatGeneration wraps the assistant message in the expected model response objects.

## 6. LangGraph: draw the path and carry a notebook

A graph resembles a school timetable with branches. State carries the work. Nodes do steps. Edges connect steps. Compilation creates an executable graph. LangGraph supports deterministic and model-driven processing; using an LLM is optional. [Official graph overview](https://docs.langchain.com/oss/python/langgraph/overview).

### Lab: an actual graph without a model account

```python
# lab: langgraph_basic
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class LessonState(TypedDict):
    question: str
    answer: str

def answer_node(state: LessonState):
    return {"answer": state["question"].strip().upper()}

builder = StateGraph(LessonState)
builder.add_node("answer", answer_node)
builder.add_edge(START, "answer")
builder.add_edge("answer", END)
graph = builder.compile()
out = graph.invoke({"question":"  learn agents  ", "answer":""})
assert out["answer"] == "LEARN AGENTS"
print(out["answer"])
```

`TypedDict` describes a dictionary's expected fields; it is not full runtime validation. The node returns a state update. START and END are graph boundaries. The two edges describe the path. `compile` prepares execution; `invoke` runs it with an initial state. Uppercasing is deliberately simple so the graph behavior is visible.

Conditional edges choose paths from state. A reducer defines how a field handles incoming updates, such as appending results rather than replacing them. Concurrent writes to one field need an appropriate merge strategy; last-writer accidents are not a coordination design. [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).

## 7. Checkpointing, interrupts, and replay

Saving a game's progress is a checkpoint. A graph checkpointer saves execution state associated with a thread identifier. Durable persistence survives process loss; an in-memory saver does not. Separate short-term workflow state from longer-term user memory. [Persistence guide](https://docs.langchain.com/oss/python/langgraph/persistence).

An interrupt pauses for input. Resuming can restart the interrupted node's body, so code before the interruption may run again. Keep irreversible effects after validated approval and use idempotency. The same thread identifier reconnects the continuation; it does not itself authorize the caller. [Interrupt semantics](https://docs.langchain.com/oss/python/langgraph/interrupts).

```python
# lab: langgraph_interrupt
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

class ReviewState(TypedDict):
    proposal: str
    approved: bool

def review(state):
    response = interrupt({"proposal": state["proposal"]})
    if type(response) is not bool:
        raise ValueError("approval must be a Boolean")
    return {"approved": response}

b = StateGraph(ReviewState)
b.add_node("review", review)
b.add_edge(START, "review")
b.add_edge("review", END)
app = b.compile(checkpointer=InMemorySaver())
config = {"configurable":{"thread_id":"lesson-review"}}
paused = app.invoke({"proposal":"Reserve demonstration book", "approved":False}, config)
assert "__interrupt__" in paused
finished = app.invoke(Command(resume=True), config)
assert finished["approved"] is True
print("Paused and resumed; no reservation was executed")
```

The state contains a proposal and a Boolean. `interrupt` exposes the exact proposal. The response is checked rather than trusting that any nonempty string means yes. The saver is intentionally temporary. The second invocation supplies the review result. This lab changes only graph state: it performs no real reservation.

## 8. Parallel agents and orchestration

If three children independently check spelling, arithmetic, and citations, they can work concurrently. If one must first produce the draft, reviewers must wait for it. Parallelize independent work, not dependencies.

Fan-out sends work to multiple workers; fan-in combines results. A supervisor assigns tasks and resolves disagreements. Handoffs transfer active responsibility. Map-reduce maps similar work across items, then reduces outputs. A pipeline passes one stage's output into the next. A DAG has no directed cycles; an agent graph may deliberately contain bounded loops.

```python
# lab: bounded_parallel_workers
import asyncio

async def worker(name, evidence, semaphore):
    async with semaphore:
        await asyncio.sleep(0)
        return {"worker":name, "evidence":evidence, "status":"ok"}

async def parallel_review():
    cap = asyncio.Semaphore(2)
    jobs = [worker("math", "2+3=5", cap),
            worker("sources", "document A", cap),
            worker("format", "JSON valid", cap)]
    return await asyncio.wait_for(asyncio.gather(*jobs), timeout=2)

results = await parallel_review()
assert [r["worker"] for r in results] == ["math","sources","format"]
print("Three simulated reviewers; at most two inside the bounded section")
```

`async` declares a coroutine; `await` yields while waiting. The semaphore caps in-flight sections. `gather` schedules and collects jobs in input order, not completion order. `wait_for` bounds the await time. These workers are deterministic simulations, not LLMs. For real requests, define cancellation, partial failures, rate limits, retries, and which missing reviewers prevent finalization.

Do not assume cancellation reverses a remote side effect. Give workers separate result fields or an explicit reducer. When parallel calls have different durations, total time approaches the slowest branch plus overhead, not the sum, only if resources and dependencies permit genuine overlap.

**Exercise:** One worker fails. Should its absence be disguised as agreement? **Answer:** No. Mark the failure and apply a predefined policy: retry, degrade with disclosure, or stop.

### Lab: actual LangGraph fan-out and fan-in

```python
# lab: langgraph_parallel_merge
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END

class ParallelState(TypedDict):
    findings: Annotated[list[str], operator.add]
    report: str

def math_check(state): return {"findings":["math: 2+3=5"]}
def source_check(state): return {"findings":["source: local lesson"]}
def combine_checks(state): return {"report":"; ".join(sorted(state["findings"]))}

parallel = StateGraph(ParallelState)
parallel.add_node("math", math_check)
parallel.add_node("source", source_check)
parallel.add_node("combine", combine_checks)
parallel.add_edge(START, "math")
parallel.add_edge(START, "source")
parallel.add_edge(["math","source"], "combine")
parallel.add_edge("combine", END)
merged = parallel.compile().invoke({"findings":[], "report":""})
assert len(merged["findings"]) == 2
assert merged["report"] == "math: 2+3=5; source: local lesson"
print(merged["report"])
```

Both branches begin from START. `Annotated` attaches a reducer: `operator.add` concatenates returned finding lists. The list-valued edge waits for the named predecessor nodes before combining. Sorting gives a deterministic display order rather than relying on scheduling. These independent functions demonstrate orchestration; their tiny workload is not a performance benchmark.

## 9. Deep Agents and the agent harness

“Deep agent” is sometimes informal terminology for a long-running agent with planning and delegation. LangChain's **Deep Agents** is also a specific package. Its harness supplies capabilities such as planning, filesystem interactions, subagents, and context management. Depth here is not the count of neural-network layers. [Official overview](https://docs.langchain.com/oss/python/deepagents/overview).

A long research task needs a plan, evidence records, intermediate artifacts, and stop criteria. File-backed context can keep detailed artifacts outside the immediate prompt. Summaries save space but may discard important evidence. A delegated subagent should receive a bounded task, permitted tools, required output structure, and budget; return evidence and uncertainty with conclusions.

### Integration recipe

```python recipe
from deepagents import create_deep_agent

def lookup_term(term: str) -> str:
    """Look up one term in the local teaching glossary."""
    glossary = {"harness":"Runtime around the model and tool loop."}
    return glossary.get(term.lower(), "No glossary entry found.")

def build_tutor(configured_tool_calling_model):
    return create_deep_agent(
        model=configured_tool_calling_model,
        tools=[lookup_term],
        system_prompt="Teach with examples. Cite actual glossary evidence.",
    )
```

The model must support the capabilities this harness uses. Filesystem and execution permissions depend on the chosen backend and deployment; a filesystem interface is not automatically an operating-system sandbox. Review exposed capabilities before using real private files. This factory pattern follows the documented entry point; provider execution remains untested in this workbook. [Quickstart API](https://docs.langchain.com/oss/python/deepagents/quickstart).

**Check:** Does giving an agent a todo list guarantee it completes the task? **Answer:** No. Completion needs observable acceptance tests and resource limits, not just a plan.

### Lab: Deep Agents harness with the same scripted model

Run after the LangChain scripted-model cell. This confirms construction and a basic tool loop in the actual package. It does not test autonomous planning, file operations, subagent quality, or every middleware capability.

```python
# lab: deepagents_scripted_model
from deepagents import create_deep_agent
deep_tutor = create_deep_agent(
    model=ScriptedStockModel(), tools=[stock_count],
    system_prompt="Use the demonstration stock tool and report its value.")
deep_result = deep_tutor.invoke({"messages":[{"role":"user","content":"Pencil stock?"}]})
assert deep_result["messages"][-1].content == "Stock result: 12"
print("Deep Agents harness completed a scripted tool round trip")
```

The factory builds the harness around an injected model and tool. The input has the same message-oriented shape. The check verifies the final response produced from the actual tool result. A real model may choose different paths and requires separate task evaluations.

## 10. MCP: a shared language for capabilities

Model Context Protocol connects an AI host with external capability servers. The host is the application; it manages clients that communicate with servers. A server can expose tools, resources, and prompts. Tools perform operations, resources provide readable context, and prompts provide reusable interaction templates. A server need not contain a model. [Official architecture](https://modelcontextprotocol.io/docs/learn/architecture).

Imagine electrical sockets: a common connection reduces custom adapters, but plugging something in does not prove the device is safe. MCP provides interoperability, not automatic authorization, truth, sandboxing, or trustworthy tool descriptions.

Client and server must agree on a supported protocol and capabilities. Versioned specifications change lifecycle details; do not combine a handshake from one revision with message fields from another. Use a compatible SDK and the recorded version. A JSON-RPC request identifies an operation and correlates a result with an ID. SDKs handle the exact envelope; do not handcraft wire messages from outdated snippets.

Local stdio uses a subprocess's input and output channels; avoid ordinary debug logging to a protocol stdout stream. HTTP transports support separately running services and introduce network identity, credentials, origin policies, and timeouts. Neither transport choice replaces application permissions.

**Working story:** A host lists available catalog tools, obtains the schema for `book_count`, calls it with `{topic:"space"}`, receives a result, then supplies that result to the model. The application must still enforce the requester's access to the underlying catalog.

## 11. FastMCP: author a server and test its client

FastMCP is a Python library for creating and consuming MCP services. The standalone package imports from `fastmcp`; the MCP Python SDK has also provided a FastMCP class under another import path. Similar names do not mean identical releases or APIs. This workbook uses the standalone package and records the installed version. [FastMCP introduction](https://gofastmcp.com/getting-started/welcome).

### Lab: real MCP calls in memory

```python
# lab: fastmcp_roundtrip
from fastmcp import FastMCP, Client

server = FastMCP("SchoolCatalog")

@server.tool
def book_count(topic: str) -> int:
    """Return a demonstration catalog count for a topic."""
    return {"space":3, "plants":2}.get(topic.strip().lower(), 0)

async def check_catalog():
    async with Client(server) as client:
        tools = await client.list_tools()
        assert "book_count" in {tool.name for tool in tools}
        result = await client.call_tool("book_count", {"topic":"space"})
        assert result.data == 3
        return result.data

count = await check_catalog()
print("MCP returned:", count)
```

The server has a human-readable name. The decorator registers the function as a tool. Type information supplies schema ingredients. The client context opens and closes its lifecycle. Listing tools checks discovery; calling the tool exercises dispatch and result handling. In-memory transport avoids sockets and credentials while testing real library behavior. [Client transport documentation](https://gofastmcp.com/clients/client).

For a separate local process, put server declarations in `server.py` and call `server.run()` inside an `if __name__ == "__main__":` guard. HTTP serving uses the documented transport configuration. The guard prevents imports from automatically starting a blocking server. The notebook lab intentionally does not expose a network endpoint. [Server quickstart](https://gofastmcp.com/getting-started/quickstart).

### Lab: resources and prompts are different primitives

Run after the FastMCP server/client cell. A resource offers content at an identifier; a prompt offers a reusable message template. Neither grants additional privileges.

```python
# lab: fastmcp_resources_prompts
@server.resource("catalog://{topic}")
def catalog_resource(topic: str) -> str:
    return f"Demonstration notes about {topic}."

@server.prompt
def study_prompt(topic: str) -> str:
    return f"Explain {topic} with one small example."

async def check_primitives():
    async with Client(server) as client:
        contents = await client.read_resource("catalog://space")
        assert "space" in contents[0].text
        prompt = await client.get_prompt("study_prompt", {"topic":"agents"})
        assert "agents" in prompt.messages[0].content.text
    return "Resource read and prompt rendered"

print(await check_primitives())
```

The resource template fills its topic from the URI. The prompt fills its topic from named arguments. The client reads the content and retrieves the rendered prompt through distinct operations. A host decides how to present or use them; fetching a prompt does not require obeying untrusted instructions inside arbitrary retrieved content.

## 12. Agent architecture principles

Separate policy, reasoning, and effects. Policy is trusted authorization and limits. Reasoning proposes next steps. Effects change the outside world. Keeping these distinct makes it possible to test authorization without trusting the model.

Use typed boundary contracts, but validate values at runtime. Give tools narrow responsibilities: `get_order(id)` is easier to audit than arbitrary database execution. Return structured errors that distinguish not found, forbidden, temporary failure, and invalid input.

Keep business facts in an authoritative service. Let context contain selected evidence with identity, version, and permissions. A summary is derived information and may be lossy. Cache keys must include relevant model, prompt, user/tenant, permissions, and freshness constraints.

Use idempotency for side effects, time budgets for calls, and bounded retries with exponential backoff and jitter for suitable transient failures. Repeating invalid credentials is not a resilience strategy. A checkpoint is not an exactly-once guarantee for remote operations.

Measure task success, supported claims, unauthorized actions, tool failures, cost per successful task, and latency percentiles. Log structured traces without indiscriminately recording secrets. Evaluate unanswerable tasks, corrupt results, tool outages, and adversarial retrieved instructions.

## 13. A complete capstone you can explain

Build a library assistant with three capabilities: search a fixed catalog, propose a reservation, and retrieve reservation status. The model may propose actions; an authenticated service owns permissions and mutations. Start with a deterministic workflow, then introduce model choice only where it helps.

State contains request ID, tenant/user identity from authentication, question, evidence IDs, proposed action, approval status, and final result. Search and availability checks can be independent only if their inputs and consistency requirements permit it. The reservation step follows validation and any required approval. A durable idempotency record connects request ID to result.

Acceptance tests: authorized available book succeeds; restricted book never reaches answer context; unknown title requests clarification; timeout after a successful reservation does not duplicate it; a malicious catalog description cannot grant a new tool; a stopped task launches no new work; citations refer to returned evidence.

**Mock interview:** Explain why a five-agent design may be worse than a two-node workflow. **Model answer:** It adds coordination and failure modes without necessarily adding independent useful work. Compare measured task success and cost under equal budgets; use delegation when specialization or independent verification justifies it.

## 14. Exercises with answers and coverage

**1. Model versus harness?** Model produces predictions or action proposals; harness manages execution, state, constraints, and tools.

**2. Why a reducer?** Multiple updates need explicit combination semantics; appending independent findings differs from overwriting a shared answer.

**3. Can a checkpoint replace an idempotency key?** No. A workflow may replay after a remote action already completed.

**4. Why not pass every tool to every worker?** It increases irrelevant choices and authority. Narrow capabilities make behavior easier to control and evaluate.

**5. Does MCP make a tool safe?** No. It standardizes communication; security remains a system property.

**6. Is async equal to multicore CPU execution?** No. Async coordinates waiting. Threads, processes, native kernels, and accelerators have different execution behavior.

**7. What is the best agent architecture?** The simplest structure meeting measured requirements under its constraints; there is no universal winner.

**8. What should a reviewer receive?** The exact proposed action, relevant evidence, expected effect, uncertainty, and permission context.

Detailed coverage: agent vocabulary, harness loop, agent types, LangChain entry point, runnable LangGraph, interrupts, bounded parallelism, Deep Agents entry point, MCP, FastMCP, orchestration, permissions, replay, evaluation, and capstone design. Advanced introductions: distributed graph persistence, large-scale scheduler internals, remote MCP authorization, sandbox backends, dynamic delegation, and model-provider adapters. These require environment-specific engineering beyond a small teaching lab.


Advanced continuation: [07-durable-agents](07-durable-agents.html). The advanced workshop and accompanying projects extend the introductory scope described above.
