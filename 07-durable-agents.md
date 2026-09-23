# Notebook 7 — Agents that survive mistakes and restarts

An ordinary chatbot is like a conversation at a desk. A dependable agent is a worker with a notebook, a permission card, a budget, and a supervisor. If the lights go out, a replacement worker must know what happened and what must not happen twice. Read Notebook 1 first; this notebook explains the machinery behind reliable action.

## 1. State, execution history, and the effect boundary

State is the information needed for the next decision: the question, retrieved evidence, proposed action, approval, and completion status. Execution history records how we arrived there. An external effect changes something outside the workflow: sending a message, reserving stock, or charging money. Saving state and performing an external effect are usually different transactions.

Suppose an agent reserves a seat and then crashes before saving “reserved.” After restart, its notebook says the reservation is unfinished. Repeating the request may reserve two seats. A checkpoint alone does not fix this. Give the operation a stable idempotency key, store that key with the reservation in the reservation service, and return the old result on a retry. Reuse the key only for the same payload; a changed payload should conflict.

There are three different guarantees. At-most-once may lose work rather than repeat it. At-least-once may repeat work and needs duplicate handling. Exactly-once observable effects require a carefully defined boundary, often a single database transaction or an idempotent receiver. Avoid claiming universal exactly-once execution across independent systems.

**Trace:** receive request → commit pending job → claim lease → perform idempotent operation → commit result. A crash between the last two steps causes a retry. An idempotent receiver makes that retry harmless.

## 2. Real LangGraph persistence and human approval

A checkpoint is a bookmark, not a frozen operating-system process. The framework reconstructs execution from saved state. Interrupts can cause the containing node to run again, so keep irreversible effects after approval and make them idempotent. Use stable thread IDs and a durable backend. The official [persistence reference](https://docs.langchain.com/oss/python/langgraph/persistence) explains the framework's checkpoint model; our example below tests reopening its SQLite store.

```python
# lab: durable_graph_approval
from typing import TypedDict
from pathlib import Path
from tempfile import TemporaryDirectory
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver

class ApprovalState(TypedDict):
    question: str
    approved: bool
    answer: str

def approve_node(state):
    decision = interrupt({'question': state['question'], 'action': 'prepare a study answer'})
    return {'approved': decision is True}

def answer_node(state):
    return {'answer': 'Approved study answer' if state['approved'] else 'Declined'}

def graph_builder():
    graph = StateGraph(ApprovalState)
    graph.add_node('approval', approve_node)
    graph.add_node('answer', answer_node)
    graph.add_edge(START, 'approval')
    graph.add_edge('approval', 'answer')
    graph.add_edge('answer', END)
    return graph

with TemporaryDirectory() as directory:
    database = str(Path(directory)/'checkpoints.sqlite')
    config = {'configurable': {'thread_id': 'alice-request-42'}}
    with SqliteSaver.from_conn_string(database) as saver:
        graph = graph_builder().compile(checkpointer=saver)
        paused = graph.invoke({'question': 'Explain checkpoints', 'approved': False, 'answer': ''}, config)
        assert paused['__interrupt__']
    # New saver and graph: the old in-memory graph is no longer relied upon.
    with SqliteSaver.from_conn_string(database) as saver:
        graph = graph_builder().compile(checkpointer=saver)
        resumed = graph.invoke(Command(resume=True), config)
        assert resumed['answer'] == 'Approved study answer'
print('Persistent approval resumed from a reopened SQLite checkpoint')
```

The interrupt payload describes the actual proposal. In a real approval system also bind the decision to the authenticated reviewer, action hash, resource version and expiry. “Yes” from the wrong person or for an old proposal is not authorization. A changed proposal needs a new decision. Do not let retrieved text, a model, or the worker manufacture approval.

## 3. Checkpoint migrations are data migrations

Imagine version 1 stores `question`, while version 2 requires `messages`. Renaming the field in code does not repair saved checkpoints. Version your application state separately from the framework's storage schema. Write a pure migration, preserve the old meaning, reject unknown future versions, test representative historic records, back up before rollout, and make rollback behavior explicit. Use framework-supported state-update APIs; do not casually rewrite its internal tables.

```python
# lab: checkpoint_state_migration
from copy import deepcopy
def migrate_state(saved):
    state = deepcopy(saved)
    version = state.get('schema_version', 1)
    if version == 1:
        state['messages'] = [{'role': 'user', 'content': state.pop('question')}]
        state['schema_version'] = 2
    elif version != 2:
        raise ValueError('unsupported state version')
    return state

old = {'question': 'Why retry?', 'schema_version': 1}
new = migrate_state(old)
assert new['messages'][0]['content'] == old['question']
assert migrate_state(new) == new and 'question' in old
try:
    migrate_state({'schema_version': 99})
except ValueError:
    print('Migration is non-mutating, repeatable, and rejects unknown versions')
else:
    raise AssertionError('future state must not be guessed')
```

Changing a graph's node names or interrupt ordering also changes execution semantics. A schema migration cannot automatically make a half-finished old workflow compatible with a new graph. Keep a versioned workflow definition available, drain old runs, or explicitly migrate their execution position. Test the paused and mid-failure states, not just newly started runs.

## 4. Leases, fencing, and recovery after a crash

A lease says “worker A may work on this job until time T.” Expiry permits recovery after A disappears. But A may be merely slow, then wake up after worker B takes over. A fencing token distinguishes A's old ownership from B's new ownership. Every database update checks the current token. A stale worker's update affects zero rows.

```python
# lab: stale_worker_fencing
import sqlite3
db = sqlite3.connect(':memory:')
db.execute('create table job(id integer primary key, token integer, answer text)')
db.execute("insert into job values(1, 1, '')")
old_token = 1
db.execute('update job set token=2 where id=1')
stale = db.execute("update job set answer='old' where id=1 and token=?", (old_token,))
fresh = db.execute("update job set answer='new' where id=1 and token=2")
assert stale.rowcount == 0 and fresh.rowcount == 1
assert db.execute('select answer from job').fetchone()[0] == 'new'
db.close()
print('Only the current lease holder can publish its result')
```

This protects database writes. If the external tool ignores the token, it can still perform an old worker's action. Combine fencing with receiver-side idempotency or conditional resource versions. The Study Coach project uses durable jobs, expiring leases, an attempt budget and token-checked updates. Its answer generation is read-only, which makes repeating computation safe.

## 5. Cancellation and parallel failures

Cancellation is a request to stop, not time travel. An already committed payment cannot be “uncalled.” Stop scheduling new work, propagate a cancellation signal, release resources in `finally`, and decide whether a compensating action is possible. Python `TaskGroup` cancels siblings when one child fails; collecting partial results needs a different explicit policy. The [Python task documentation](https://docs.python.org/3/library/asyncio-task.html) specifies these cancellation rules.

```python
# lab: parallel_failure_cleanup
import asyncio
async def failure_demo():
    started = asyncio.Event()
    cleaned = []
    async def slow():
        try:
            started.set()
            await asyncio.sleep(30)
        finally:
            cleaned.append('released')
    async def broken():
        await started.wait()
        raise ValueError('retriever failed')
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(slow())
            group.create_task(broken())
    except* ValueError:
        pass
    assert cleaned == ['released']
await failure_demo()
print('A failed child cancelled its sibling and cleanup ran')
```

For an all-required workflow, one missing branch invalidates the combined result. For best-effort search, return successful branches with explicit missing-source information. Never silently label a partial answer complete. Bounded parallelism controls concurrency; a deadline controls duration; a token/tool budget controls expenditure. They solve different problems. Add queue limits too: ten running tasks plus a million queued tasks can still exhaust memory.

## 6. Memory with ownership, expiry, and evidence

Working memory is the current task state. Episodic memory records past events. Semantic memory stores facts. Procedural memory stores instructions or skills. Retrieval indexes are access paths, not automatically trustworthy memories. A useful record has owner, source, creation time, expiry, confidence or verification state, and a deletion policy.

```python
# lab: scoped_memory
from dataclasses import dataclass
@dataclass(frozen=True)
class Memory:
    owner: str
    text: str
    expires: int
    verified: bool

def recall(records, owner, now):
    return [m.text for m in records if m.owner == owner and m.expires > now and m.verified]

memories = [Memory('alice', 'prefers small examples', 20, True),
            Memory('bob', 'private plan', 20, True),
            Memory('alice', 'old preference', 9, True),
            Memory('alice', 'unverified claim', 20, False)]
assert recall(memories, 'alice', 10) == ['prefers small examples']
print('Owner, expiry and verification filters applied before recall')
```

Summaries compress information and can lose a critical negation, date or source. Keep links to original evidence and distinguish user facts from model inferences. Do not store secrets simply because they appeared in a conversation. Updating a preference should supersede the old preference rather than create contradictory permanent facts. Test deletion from source storage, caches and indexes.

## 7. Systematic evaluation instead of impressive demos

Build a versioned task set with ordinary cases, ambiguous requests, malicious retrieved instructions, missing evidence, denied tools, timeouts, repeated delivery and cancellations. Keep development cases separate from held-out evaluation. Grade task success, groundedness, permission violations, tool-call count, latency and cost. A single average hides dangerous categories; report them separately.

```python
# lab: agent_evaluation_gate
cases = [
    {'category': 'normal', 'success': True, 'violation': False, 'calls': 2},
    {'category': 'denied', 'success': True, 'violation': False, 'calls': 0},
    {'category': 'timeout', 'success': False, 'violation': False, 'calls': 3},
    {'category': 'injection', 'success': True, 'violation': False, 'calls': 0},
]
success_rate = sum(c['success'] for c in cases)/len(cases)
assert success_rate == 0.75
assert not any(c['violation'] for c in cases)
assert max(c['calls'] for c in cases) <= 3
print({'success_rate': success_rate, 'permission_violations': 0, 'cases': len(cases)})
```

Four invented records explain the calculation; they are not evidence of a production agent's quality. Real evaluation runs the candidate on stored inputs and captures traces. Repeat nondeterministic tasks, report sample sizes and uncertainty, and have humans audit rubric disagreements. An LLM judge can be biased, prompt-injected or inconsistent. Calibrate it against human labels. Compare a simple workflow, a single agent and a multi-agent design under the same budgets before adopting delegation.

The companion `labs/agent-evaluation/evaluate.py` runs an actual versioned 16-case regression dataset against the connected application's retrieval function. Ten cases check first-ranked evidence, four check cross-owner exclusions including instruction-like queries, and two check the no-evidence path. It records category scores, latency, returned IDs and a hash of the evaluated source. Run it from the notebook environment and inspect `evaluation-report.json`. This is an executable development regression gate, not a held-out estimate of LLM reasoning quality; its small size and deterministic baseline are explicit.

## 8. Architecture decisions and graded exercise

**Question, 10 points:** Two research workers run in parallel. One times out. The user approved a report before the evidence changed. The first publisher crashed after writing the report. Design recovery.

**Answer:** Define whether both branches are required (2). Mark missing evidence if partial output is allowed (1). Revalidate approval against the exact new proposal and resource version (2). Publish using a stable idempotency key and reject changed payloads (2). Recover via a durable lease and fence stale writes (2). Record the attempt, failure and outcome without leaking credentials (1).

**Follow-up:** Why not just retry the entire graph? Because replay may repeat effects, consume extra budget and invalidate prior approvals. A successful retry also does not prove the original attempt failed.

**Mastery task:** In Study Coach, approve a job, stop the Java process while the status is running, restart with the same database, and watch the attempt count. Cancel another job and verify that a stale worker cannot change it to done. Read the automated restart test before repeating this manually.
