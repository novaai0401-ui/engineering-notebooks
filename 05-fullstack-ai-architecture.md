# Notebook 5 — Full-Stack Java, Python, React, and AI Engineering

This notebook teaches how the parts cooperate. A system is more than a collection of framework names. We use one story throughout: a learning portal where users manage study topics and ask for explanations supported by course notes. The labs are local teaching examples; the architecture sections describe what must be added for a real service.

## 1. Start from the user's journey

A learner opens a dashboard, signs in, selects a topic, asks a question, receives an explanation with sources, and records completion. Each step has a user-visible result and a possible failure. Begin with these outcomes before drawing microservices.

React presents forms, progress, and results. A Java service owns users, study records, permissions, and transactional business actions. A Python service handles retrieval, model inference, and model-specific evaluation. A database stores authoritative records. Object storage can hold documents; a search index supports retrieval. A queue can manage long-running jobs.

This division is an example, not a requirement that Java and Python must both appear in every system. A single language and a modular monolith may meet the same requirements more simply.

```text
Browser / React
      |
 HTTPS + authenticated request
      v
Java API ------> relational database
      |
 authorized internal request
      v
Python AI service ---> allowed document retrieval ---> model adapter
      |
 structured answer + evidence + status
      v
Java response ---> React loading/error/success display
```

**Practice:** Should Python trust a user ID sent directly by the browser without verification? **Answer:** No. Identity must come from an authenticated and authorized boundary, not an arbitrary field.

## 2. Contracts are agreements between teams

An API contract says what inputs are accepted, what outputs mean, how errors are represented, and which guarantees exist. A typed schema is part of it; permissions and timing semantics are also part of it.

For an explanation request, define question, course ID, request ID, and supported options. Derive identity from the authenticated context. For a response, include status, answer, evidence identifiers, and a request ID. A citation should refer to evidence actually provided, not a made-up URL.

```json
{
  "request_id": "r-123",
  "status": "complete",
  "answer": "A gradient describes local rates of change.",
  "evidence": [{"document_id":"math-1", "version":2}],
  "warnings": []
}
```

Document whether complete means generation finished or the business task succeeded. Version schemas intentionally. Additive optional fields are often easier to evolve than changing the meaning of an existing field. Clients must not assume every error body matches the success shape.

**Exercise:** A service returns HTTP 200 with `{error:"failed"}` to every failure. Why is that harmful? **Answer:** Transport status and business meaning disagree, monitoring becomes misleading, and clients may treat failures as success.

## 3. SQL, keys, joins, and indexes

A relational table stores rows with named columns. A primary key identifies a row. A foreign key constrains a relationship. A unique constraint protects a business uniqueness rule. SQL selects, joins, groups, and changes records. Parameterized queries separate data from SQL syntax.

```python
# lab: relational_integrity
import sqlite3
db = sqlite3.connect(":memory:")
db.execute("PRAGMA foreign_keys=ON")
db.execute("CREATE TABLE learner(id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
db.execute("""CREATE TABLE topic(
  id INTEGER PRIMARY KEY,
  learner_id INTEGER NOT NULL REFERENCES learner(id),
  title TEXT NOT NULL,
  UNIQUE(learner_id, title)
)""")
with db:
    db.execute("INSERT INTO learner VALUES (?,?)", (1,"Asha"))
    db.execute("INSERT INTO topic VALUES (?,?,?)", (10,1,"Gradients"))
row = db.execute("""SELECT l.name,t.title FROM learner l
 JOIN topic t ON l.id=t.learner_id WHERE l.id=?""", (1,)).fetchone()
assert row == ("Asha","Gradients")
try:
    with db:
        db.execute("INSERT INTO topic VALUES (?,?,?)", (11,1,"Gradients"))
except sqlite3.IntegrityError:
    pass
else:
    raise AssertionError("duplicate should be rejected")
db.close()
print("Join and uniqueness rule verified")
```

The database is temporary and in memory. Foreign keys are explicitly enabled for this SQLite connection. Placeholders carry data separately from the query. The transaction context commits or rolls back appropriately. The uniqueness rule is enforced in storage, not just by an earlier application check.

An index is an auxiliary lookup structure. It speeds some reads but adds write and storage costs. Composite index order affects which predicates and orderings it supports. Inspect plans and representative data. Normalization reduces duplicated facts and update anomalies; denormalization can speed selected reads at the cost of consistency work.

## 4. Transactions and distributed work

A local database transaction can atomically record a study update. It cannot automatically make a remote model call and a message broker commit part of the same transaction. Distributed boundaries require explicit failure design.

The outbox pattern records a business change and an event in the same database transaction. A relay later publishes the event. Publication can happen more than once, so consumers need idempotency. A saga coordinates a sequence of local transactions with compensating actions where feasible; compensation is not identical to restoring the world as if nothing happened.

CQRS separates command and query models. Event sourcing stores state-changing events as the source of truth and derives current views. You can use an outbox without event sourcing and CQRS without multiple deployed services. Do not bundle unrelated patterns merely because they often appear in conference diagrams.

**Failure story:** The service reserves a place, publishes an event, then crashes before acknowledging. A retry must not reserve another place. Persistent uniqueness and request identity handle this better than hoping the network delivers exactly once.

## 5. Idempotency and request identity

An idempotency key identifies one logical operation. Bind it to the authenticated scope and the operation payload. Reusing the same key for a different request should be rejected rather than returning an unrelated old result.

```python
# lab: idempotent_operation
import hashlib, json
records = {}
effects = []

def perform_once(user, key, payload):
    identity = (user, key)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if identity in records:
        old_digest, result = records[identity]
        if old_digest != digest:
            raise ValueError("key reused with different payload")
        return result
    result = {"operation_id": len(effects)+1, "topic":payload["topic"]}
    effects.append(result)
    records[identity] = (digest, result)
    return result

first = perform_once("user-1", "key-1", {"topic":"agents"})
second = perform_once("user-1", "key-1", {"topic":"agents"})
assert first == second and len(effects) == 1
try:
    perform_once("user-1", "key-1", {"topic":"databases"})
except ValueError:
    pass
else:
    raise AssertionError("conflicting retry accepted")
print("Sequential retry did not duplicate the demonstration effect")
```

This demonstrates semantics, not production durability or concurrency safety. A real implementation needs transactional persistence, uniqueness, in-progress status, crash recovery, and a defined retention period. The toy can lose everything on restart and race under concurrent access. Returning references to mutable cached values also needs defensive handling in a deployed design.

## 6. Authentication, authorization, and trust boundaries

Authentication answers who the caller is. Authorization answers whether that caller may perform this action on this object. Enforce both at the authoritative service. Never take a model's statement that permission exists as evidence.

Browser sessions can use secure cookie-based designs with appropriate CSRF defenses. Token-based API designs require signature/issuer/audience/expiry checks and safe storage. Service-to-service identity should be explicit; a forwarded user identifier alone is not authenticated delegation.

Restrict document retrieval by tenant and entitlement before evidence reaches a model or logs. A secret excluded from the final answer can still leak through prompts, telemetry, or caches. Separate secret management from model-visible context.

Use parameterized SQL, output encoding, controlled file paths, upload limits, and dependency hygiene. An AI feature inherits ordinary application-security responsibilities and adds prompt-injection and model-output risks. A model's generated SQL or code is a proposal, not something to execute with unlimited authority.

## 7. A permission-aware retrieval lab

```python
# lab: authorized_retrieval
docs = [
    {"id":"public","tenant":"school-A","text":"gradient slope", "roles":{"student","teacher"}},
    {"id":"exam","tenant":"school-A","text":"gradient exam answers", "roles":{"teacher"}},
    {"id":"other","tenant":"school-B","text":"gradient notes", "roles":{"student"}},
]

def retrieve(query, authenticated_tenant, authenticated_role):
    terms = set(query.lower().split())
    allowed = [d for d in docs if d["tenant"] == authenticated_tenant
               and authenticated_role in d["roles"]]
    return sorted(allowed,
        key=lambda d: len(terms & set(d["text"].split())), reverse=True)

found = retrieve("gradient", "school-A", "student")
assert [d["id"] for d in found] == ["public"]
print("Restricted and cross-tenant documents excluded before ranking")
```

Identity arguments in this lab represent already-verified server context. The function itself does not authenticate a browser. Filtering precedes ranking so restricted documents never become candidate evidence. The score is transparent word overlap, not a semantic embedding model. Production needs versioning, expiry, policy updates, authorization-aware caching, and tests for permission changes.

## 8. ML and generative AI service design

A predictive model maps inputs to scores or estimates. A generative model produces structured or unstructured outputs. An agent adds action selection and tool execution around a model. Do not turn a deterministic lookup or calculation into an expensive agent loop without a measured reason.

Training pipelines need data versions, split definitions, preprocessing, configuration, metrics, and model artifacts. Serving needs validated input, the matching preprocessing, stable output contracts, monitoring, and rollback. Training-serving skew means the deployed transformation differs from the training transformation.

For RAG, separate corpus preparation, retrieval, reranking, context assembly, generation, and citation checking. For fine-tuning, define a held-out task distribution and evaluate regressions. For agents, evaluate task completion and unauthorized actions, not just fluent responses.

Use a provider adapter so business logic does not depend on one SDK response shape. Record model identity and generation settings. A retry can produce different text; nondeterminism is part of the interface. Validate structured output semantically even when the JSON syntax is guaranteed.

## 9. Queues, streaming, cancellation, and backpressure

Long work should not require an unbounded browser request. A job API can accept work with 202, return a job ID, and expose status. Workers claim jobs and update states such as queued, running, succeeded, failed, or cancelled. Job IDs are not authorization tokens.

Server-sent events are useful for one-way server-to-browser updates. WebSockets support bidirectional messaging with different connection-management needs. Streaming requires event IDs, reconnect semantics, and clear terminal states. Showing partial tokens does not mean the entire operation succeeded.

Backpressure prevents a faster producer from overwhelming a slower consumer. Bound queue length, worker concurrency, per-tenant demand, and memory. Cancelling the UI's fetch does not necessarily stop a background job. Define cancellation at each layer and avoid launching new side effects once cancellation is accepted.

**Exercise:** A reconnect receives the last event twice. What should the UI do? **Answer:** Deduplicate or apply events idempotently using a stable event identity, consistent with the stream contract.

## 10. Caching, retries, circuit breakers, and rate limits

A cache saves repeated work but creates freshness and isolation questions. Define key, value, TTL, invalidation, and failure policy. Include tenant/permission context where outputs depend on it. A cache hit for another user can be a disclosure, not a performance success.

Retries help transient failures when repeating is safe. Use bounded exponential backoff with jitter, honor applicable retry hints, and enforce an overall deadline. Retry storms can overload recovering services. A circuit breaker opens after selected failures and later probes recovery. A bulkhead caps resource sharing so one dependency cannot consume the whole service.

Rate limits control arrival over time. A token bucket refills capacity at a rate and allows a bounded burst. A concurrency limit bounds simultaneous work. These solve different problems. Limiting to ten requests per second does not prevent thousands of very long requests accumulating.

## 11. Observability and evaluation

Logs record events, metrics aggregate measurements, and traces connect steps within a request. Use request/job IDs and structured fields. Protect sensitive inputs and outputs; indiscriminate logging can create a second private-data store.

Report task success, correctness, citation support, invalid tool calls, permission failures, retries, p50/p95 latency, and cost per successful task. A low cost per token can be misleading if the model needs many retries or causes more support work.

Evaluation datasets should include ordinary cases, ambiguous questions, unanswerable cases, stale documents, conflicting evidence, malformed inputs, and dependency failures. Keep a final held-out set and avoid repeatedly tuning prompts directly to it. Slice by relevant groups and data conditions rather than relying only on one average.

## 12. Deployment, containers, and CI/CD

A container packages an application and its dependencies in an isolated process environment using operating-system mechanisms. It is not automatically a strong sandbox for arbitrary hostile code. Images should be reproducible, minimal enough for purpose, and scanned under your process. Avoid baking secrets into image layers.

CI runs checks on changes. CD prepares or deploys validated artifacts under a release policy. Keep unit tests fast, integration tests representative, and end-to-end tests focused on critical journeys. Database migrations need backward/forward compatibility planning across rolling versions.

Blue/green deployment switches between environments. Canary deployment shifts a fraction of traffic and observes outcomes. Rollback must account for schema and data changes; restoring an old binary does not undo every new write. Feature flags decouple selected behavior activation from code deployment but add configuration combinations to test.

## 13. End-to-end capstone specification

Build the learning portal with these slices, completing one user journey at a time.

| Slice | React | Java | Python | Acceptance condition |
|---|---|---|---|---|
| Topics | Form and list | CRUD with ownership | Not needed | One user cannot change another's topic |
| Explanation | Question and result view | Authenticate and route | Retrieve allowed notes, produce answer | Evidence IDs match authorized notes |
| Long work | Job status and cancel | Job ownership and lifecycle | Worker execution | Cancellation stops new work |
| Progress | Completion control | Idempotent update | Not needed | Retrying does not duplicate an event |
| Evaluation | Admin results view | Authorized access | Batch eval runner | Regressions have reproducible examples |

The included independent labs teach the primitives. This specification is not claimed to be a completed production deployment. To build it, start with a deterministic Python explanation adapter and replace it with a model only after permission, error, and retry behavior is tested.

For a timed design interview, spend the first minutes clarifying scale, latency, freshness, users, permissions, and failure costs. Give a small viable architecture, then explain how measured constraints would justify queues, replicas, caches, or service separation.

## 14. Exam answers and coverage

**Why two backend languages?** Sometimes Java business infrastructure and Python model tooling justify it; otherwise the extra boundary may not be worthwhile.

**Can a distributed system promise exactly once just by using a queue?** Not in a general end-to-end sense. Define delivery and effect semantics, durable identity, and transactional boundaries.

**Where should authorization live?** At trusted service boundaries and object-level operations, including retrieval filters and mutations.

**Why distinguish cache TTL from correctness?** A recent cached result can still be wrong for the current user's permissions or changed business state.

**What is a modular monolith?** One deployment with explicit internal module boundaries; it need not be an unstructured codebase.

**How do you evaluate an AI system?** Test the whole user task and individual stages under real constraints, including unsupported answers, authority violations, failures, and cost.

Detailed coverage: request paths, contracts, SQL, transactions, idempotency, identity, retrieval permissions, model-service separation, streaming, queues, resilience, observability, deployment, and capstone design. Advanced introductions: consensus, multi-region databases, Kubernetes internals, hardware scheduling, and formally verified distributed protocols. No finite notebook can exhaust all distributed-system designs.


Advanced continuation: [14-fullstack-workshop](14-fullstack-workshop.html). The advanced workshop and accompanying projects extend the introductory scope described above.
