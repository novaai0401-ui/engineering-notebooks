# 28 — Put the pieces together: a full-stack engineering capstone

## 1. The product story

Build a study platform. A learner logs in, asks a question about permitted course material, watches progress, receives an answer with evidence and can return later to see the saved result. An instructor updates material. An operator can investigate a failed job without reading every learner's private prompt.

The integrated Study Coach project already connects React, Java and Python with authentication, durable jobs, retrieval and browser tests. Kafka and the real-time/cache project are additional working labs. Their components are not silently wired into that existing application. Integration is a separate change requiring data contracts and end-to-end tests.

## 2. Trace one request through the architecture

React sends a CSRF-protected command with a logical request ID to Java. Java authenticates, authorizes, validates and atomically stores the job and outbox event. A publisher delivers the event. A worker loads the authorized source context and calls Python's retrieval/model boundary with a deadline. It conditionally stores the result and emits a progress event. SSE or WebSocket delivers authorized updates; a snapshot endpoint repairs missed history.

PostgreSQL owns durable business records. Kafka can carry replayable events. Redis can cache permitted projections or support a specifically designed shared session mechanism. Object storage can hold large original files while PostgreSQL stores metadata and access rules. A vector index supports retrieval. Each component adds operational responsibility; use it only when a requirement justifies it.

## 3. Contracts before frameworks

Define identifiers, ownership, schema versions, timestamps, status transitions, error codes, retryability and idempotency. A job may be queued, running, completed, failed or cancelled; decide which transitions are legal and who can make them. A completed result should not be overwritten by a late retry from an earlier worker generation.

```python
# lab: capstone_state_machine
allowed={'queued':{'running','cancelled'},'running':{'completed','failed','cancelled'},
         'failed':{'queued'},'completed':set(),'cancelled':set()}
job={'state':'queued','version':0}
def change(expected_version,target):
    if job['version']!=expected_version or target not in allowed[job['state']]:return False
    job.update(state=target,version=expected_version+1);return True
assert change(0,'running')
assert not change(0,'cancelled')
assert change(1,'completed')
assert not change(2,'running')
print(job)
```

This is a single-process model. Production compare-and-change belongs in an atomic database statement/transaction, not a read-then-write across two HTTP calls.

## 4. Full-stack skills that sit between the frameworks

Understand HTTP methods/statuses, DNS, TLS, reverse proxies, cookies, CORS, CSRF and browser storage. Know HTML semantics, responsive CSS, forms, focus management and JavaScript runtime behavior. Use TypeScript to express boundaries but still validate untrusted runtime JSON. Learn Git, reproducible builds, dependency updates, configuration management and rollback.

For APIs, cover REST resource design, pagination, validation, error envelopes, rate limits and compatibility. GraphQL can support client-shaped queries but needs authorization, query-cost limits and N+1 prevention. gRPC can suit typed service calls, with explicit deadline and compatibility handling. Choose a protocol according to clients and operational constraints rather than collecting every protocol in one request path.

For data, cover schema ownership, migrations, connection budgets, query plans and backups. For AI, cover token/context budgets, source permissions, model versioning, evaluation, prompt injection and cost limits. For operations, cover build provenance, logs/metrics/traces, deployment health and incident response.

## 5. A staged implementation route

Stage one: run the existing integrated app and explain each request without AI help. Stage two: implement one database invariant and a failing regression test. Stage three: substitute an event transport behind a clear interface, preserving outbox/inbox behavior. Stage four: add a bounded shared cache with a freshness policy. Stage five: add replayable real-time delivery and a reconnect test. Stage six: package and execute containers. Stage seven: deploy into an authorized staging environment, collect telemetry and rehearse recovery.

Each stage has a concrete exit condition. A YAML file is not the exit condition for deployment; a running, tested release is. A cache class is not the exit condition for cache reliability; demonstrated invalidation and bounded behavior are. Do not mark a stage complete merely because a chapter explains it.

## 6. Failure matrix for the capstone

| Failure | Expected behavior | Evidence to collect |
| --- | --- | --- |
| Response lost after commit | Same request ID returns original job | One durable job and stable result |
| Event delivered twice | One business effect | Inbox/unique constraint and duplicate test |
| Worker dies mid-job | Lease/recovery policy applies | State before/after restart and no lost accepted work |
| Database unavailable | Bounded error/backpressure | Deadlines, pool metrics, recovery |
| Model produces unsupported claim | Evaluation rejects release/default path | Claim-level failure record |
| Stream reconnects after retention | Snapshot/resync, explicit state | Cursor test and UI recovery |
| Permission revoked | Unauthorized reads/streams stop under policy | Tests on every relevant instance |
| Cache unavailable | Bounded fallback or explicit failure | Backend load and error budget impact |
| Deployment partially rolls out | Compatible contracts or controlled rollback | Old/new version coexistence tests |

## 7. Interview rounds and scoring

Round A, 30 minutes: implement duplicate-safe job submission and tests. Round B, 20 minutes: diagnose a stale cache race. Round C, 40 minutes: design the platform for an explicit workload, then handle a regional dependency failure. Round D, 20 minutes: explain one algorithm with an invariant, complexity and edge cases. Round E, 15 minutes: interpret a SQL query plan and fix N+1 behavior.

For each round award 0–4 in correctness, explanation, failure handling, testing and tradeoffs. Zero means absent/incorrect; one means memorized but not workable; two means a basic working answer; three means a justified tested answer; four means it remains coherent under follow-up changes. Keep the transcript, feedback and a fresh repeat attempt. Scores must come from your submitted work, not a prefilled success label.

## 8. What completion means

Reading completion means you can explain each chapter's worked example. Lab completion means you can reproduce results and deliberately trigger its failure cases. Project completion means the integrated application meets its stated acceptance tests. Interview readiness means repeated unaided performance against representative roles. None promises every possible exam or permanent coverage of a changing field.

Use the evidence report to distinguish completed local tests from cloud, physical-device, clustered identity and endurance work still needing execution. Keep that distinction visible as the library grows. The database notebook is a separate deepening path; return to the capstone and apply its modelling, transaction and indexing lessons to one real endpoint.
