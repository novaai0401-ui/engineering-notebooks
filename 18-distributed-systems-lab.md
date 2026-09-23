# 18 — Many workers, one trustworthy result

## 1. Two children take the same chore card

If two helpers both see “wash the cups,” both may start. Looking at the card is not enough: one helper must claim it atomically. A database update with a condition is the claim. If one row changes, you won. If zero rows change, another helper changed the state first.

Study Coach uses persisted jobs, an expiry time and a random lease token. Each write checks both the running state and that token. A crashed worker's lease can expire so another worker can claim the job. The old worker may wake up later; its obsolete token prevents it from overwriting the new result. This is fencing.

Fencing in our database does not magically fence an external bank or email server. External effects need their own idempotency or fencing support. “Exactly once” must always name the boundary where the guarantee holds.

## 2. A transaction is a sealed envelope

Approving a job changes its status and adds an event to an outbox table in one database transaction. Either both changes commit or neither does. Without this, the application could approve a job, crash before sending a message and lose the work forever.

A relay reads unpublished events, publishes to the durable broker, then marks them published. It can crash after publishing but before marking. Therefore delivery may repeat. This is deliberate at-least-once delivery. The consumer checks a durable inbox and the job's terminal state, so repeated messages do not repeat an already committed result.

There is no atomic transaction spanning our PostgreSQL commit and broker acknowledgment. We avoid pretending otherwise by making the consumer tolerant of repetition. For an irreversible external action, use an external idempotency key and store its outcome. A local inbox inserted before an uncommitted external action can lose work; an inbox inserted afterwards can permit duplicates. Explain that gap in an interview.

## 3. The concrete application path

The HTTP service validates the authenticated owner and CSRF token. A request idempotency key is unique per owner and binds the original question. Approval changes the job and inserts an outbox event. A relay sends the event to the `coach.jobs` queue. Two separate Java processes can listen to that queue. The winner claims the job, calls Python, streams deltas into PostgreSQL, commits the terminal status and records the inbox receipt.

The runnable topology is in `labs/study-coach/test_distributed.py`. It creates its own PostgreSQL cluster, launches a persistent ActiveMQ broker, starts Python and two Java processes, tests a broker outage, republishes an event, applies concurrent requests and restores a backup into a different database. It stops only the processes it started.

The broker is a separate process using the same packaged Java dependencies. It requires a generated password and binds to loopback. These local credentials do not establish production queue-level authorization, encryption or a high-availability broker cluster. Those need explicit configuration for the chosen environment.

## 4. The retry clock and the lease clock

A lease must remain valid while the legitimate worker is active. A fast extractive response may fit a short lease; a large model loading from disk may take much longer before its first token. Either renew the lease independently while computing or choose a bounded lease longer than the maximum execution deadline. Renewing only when tokens arrive leaves a gap before the first token.

Our default teaching worker renews on deltas. For the optional live model, increase both the read deadline and lease consistently; the live-model integration documents its settings. This is a tradeoff: a longer lease makes crash recovery slower. Production designs often use a heartbeat with a strict maximum task lifetime and cancellation.

Retries need a bounded delay and attempt count. A message broker's redelivery limit and a database job's attempt limit are separate budgets. If redelivery is exhausted while another worker holds a lease, work may land in a dead-letter queue even though the job is unfinished. The relay reconciles expired, unfinished jobs by making their outbox events publishable again, while enforcing the persisted three-attempt execution budget. Monitor dead letters and reconciliation separately; a connection-retry loop is not an unlimited business-action budget.

```python
# lab: fence_old_worker
state={'status':'pending','token':None,'answer':''}
def claim(token):state.update(status='running',token=token)
def write(token,text):
    if state['status']!='running' or state['token']!=token:return False
    state['answer']=text;return True
claim('first');claim('replacement')
assert not write('first','late wrong answer')
assert write('replacement','current answer')
state['status']='cancelled';assert not write('replacement','too late')
print('Stale and cancelled writes rejected. Real shared claims require conditional SQL.')
```

## 5. Isolation: two doctors cannot both leave

There are two doctors on call. Each transaction reads “two doctors available,” then turns its own doctor off call. The writes touch different rows, so simple row write-conflict detection may not stop both. The invariant “at least one doctor remains” breaks. This is write skew.

PostgreSQL SERIALIZABLE can reject a dangerous combination with a serialization failure. Your application must retry the complete transaction from fresh reads, not merely repeat its final update. Another option is to lock a shared guard row before making the decision, which serializes access to that invariant. Which approach is better depends on contention and the business model.

READ COMMITTED gives a new snapshot for each statement. REPEATABLE READ gives a stable transaction snapshot but does not generally eliminate write skew. SERIALIZABLE aims for an outcome equivalent to some serial execution and may abort transactions to achieve it. These statements describe PostgreSQL behavior; database engines differ. The included isolation test uses an actual PostgreSQL server rather than inferring semantics from H2.

## 6. Backups are promises until restored

A successful backup command proves a file was written. A restore test proves the file can reconstruct something usable. The example uses `pg_dump` in custom format, creates a separate database, restores it and compares job count. A stronger test also compares business checksums, constraints, roles, extensions and application behavior.

Recovery point objective asks how much recent data you may lose. Recovery time objective asks how long recovery may take. Logical dumps alone do not provide arbitrary point-in-time recovery; that typically needs base backups and retained write-ahead logs. Store backups separately from the machine they protect and test access when ordinary credentials are unavailable.

## 7. Cancellation and compensation

Cancellation is a request to stop future work, not time travel. If a message was already delivered or a tool already charged a card, changing a status cannot erase the effect. A compensating action is a new business operation, such as a refund, with its own validation and failure handling.

Use a saga when a business operation spans services without one database transaction. Record each step and its outcome; define compensations; handle partial compensation failures; make every command idempotent. A saga is appropriate for independent services, but it is unnecessary complexity when a single ordinary transaction can cover the invariant.

## 8. Timed system-design exercise

In 20 minutes, design a document-processing service for 10,000 jobs per day. First estimate average and peak arrival rates and job durations. Daily volume alone is insufficient for capacity. Define ownership, idempotency and a state machine before choosing a broker. Then explain approval, queue publication, worker claim, progress streaming, cancellation, retries, dead letters and reconciliation.

Scoring out of 10: two for a clear invariant and state machine; two for atomic job/outbox commit; two for duplicates and external effects; two for bounded retries, cancellation and leases; two for metrics and recovery tests. A diagram full of product names without these guarantees earns little credit.

Reference provenance: [Spring JMS integration](https://docs.spring.io/spring-boot/reference/messaging/jms.html). The implementation uses ActiveMQ Classic; it does not claim RabbitMQ-specific acknowledgment behavior.
