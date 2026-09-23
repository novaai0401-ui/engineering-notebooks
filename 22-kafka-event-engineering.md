# 22 — Kafka: a shared notebook that many teams can read

## 1. The classroom story

Imagine a teacher writes every classroom event in a notebook: a child joined, a book was borrowed, a book was returned. The librarian reads these events to update inventory. The head teacher reads the same events to count attendance. Reading a page does not erase it. Each reader keeps a bookmark.

Kafka is an event log with those properties. A producer appends records. A topic names a stream. Partitions divide that stream into ordered logs. A consumer reads records. An offset is a position inside one partition. A consumer group remembers its progress independently from other groups. Retention eventually removes old log data according to policy; Kafka is not automatically an everlasting archive.

Use this model before memorizing settings. A traditional work queue emphasizes distributing jobs and acknowledging delivery. Kafka emphasizes retained streams, independent readers, partition ordering and replay. Both can process jobs, but their operational tradeoffs differ.

## 2. A key chooses an ordering lane

Suppose every event for order 7 uses key `order-7`. A consistent partitioner normally puts those events in the same partition. Their order is preserved in that partition under the producer and consumer configuration's guarantees. There is no global ordering across all partitions. Adding partitions can change key mapping; plan ordering-sensitive migrations explicitly.

Two consumers in one group divide partitions. In the traditional assignment model a partition belongs to one active member in that group at a time. With two partitions and five consumers, some consumers have no partition work. A different group can independently read the same records.

```python
# lab: partition_ordering
import hashlib
def lane(key,count):return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big')%count
events=[('order-7','created'),('order-8','created'),('order-7','approved')]
partitions=[[] for _ in range(3)]
for key,value in events:partitions[lane(key,3)].append((key,value))
assert [v for k,v in partitions[lane('order-7',3)] if k=='order-7']==['created','approved']
print('Same-key order retained inside its lane. This teaching hash is not Kafka’s default partitioner.')
```

## 3. Acknowledgment, replication and durability

Each partition has a leader and may have replicas. In-sync replicas are the followers considered sufficiently caught up. With `acks=all`, a producer waits for the required in-sync replication acknowledgment. `min.insync.replicas` constrains when writes may proceed. Replication factor three with minimum in-sync replicas two is a common teaching example: it can sacrifice write availability when too few replicas remain to preserve the intended durability policy.

`acks=all` on a one-node development broker is not three-node fault tolerance. Acknowledgment also does not eliminate every storage or infrastructure failure. Define whether you are protecting against a process crash, machine loss, disk corruption or an entire region disappearing.

The supplied native exercise uses one local KRaft broker and plaintext loopback listeners. It tests real transactions, offsets, consumer assignment and restart persistence. It does not certify replication or production security. The pinned version is Kafka 4.1.2, a deliberately versioned teaching runtime rather than a claim to be the newest release.

## 4. KRaft and the control plane

Kafka's controllers maintain cluster metadata: brokers, partition leadership and configuration. KRaft manages that metadata through a replicated consensus log. The data brokers store event partitions. A small development process may act as both controller and broker. Production topology should account for the availability and capacity requirements of both roles.

The native harness creates a private storage directory, formats it with a cluster ID, starts Kafka using Java, then kills and restarts its own broker process. Never reformat an existing cluster's storage to “fix” a startup problem. Formatting is initialization, not recovery.

Run `mvn package` in `labs/kafka-lab`, then run `python labs/kafka-lab/run.py` from the library root with the documented Python environment. The harness uses ports 19092 and 19093 and refuses occupied ports. Build dependencies stay outside the ZIP.

## 5. Three meanings of duplicates

A producer can retry a request whose acknowledgment was lost. Kafka's idempotent producer protocol prevents certain duplicate appends caused by those retries. An application can also deliberately send the same business event twice in two distinct sends; producer idempotence does not identify those as the same business operation. Finally, a consumer can execute work and crash before committing its offset, causing redelivery.

Use a stable business event ID and an inbox uniqueness constraint for the third case. Bind an HTTP idempotency key to the caller and request payload for the second. The first is addressed by appropriate producer configuration. These controls complement each other.

## 6. Offsets are the next bookmark

If a consumer has successfully processed offset 12, it normally commits 13: the next position to read. Commit before the business effect and a crash can lose that effect. Commit after the effect and a crash can repeat it. For a database effect, store the event ID and effect in one database transaction, then commit the Kafka offset. Redelivery finds the inbox record and becomes harmless.

```python
# lab: consumer_inbox
ledger=[];inbox=set()
def apply(event):
    if event['id'] in inbox:return False
    # These two writes must be ONE transaction in a real database.
    ledger.append(event['amount']);inbox.add(event['id']);return True
e={'id':'payment-7','amount':250}
assert apply(e) and not apply(e);assert sum(ledger)==250
next_offset=12+1;assert next_offset==13
print('One business effect despite redelivery; commit the next offset after durable processing.')
```

## 7. Kafka transactions and their boundary

A transactional producer can commit several Kafka writes atomically or abort them. A consumer using `read_committed` does not expose aborted transactional records. A consume-transform-produce application can include consumed offsets in the Kafka transaction. This supports exactly-once processing semantics within the configured Kafka boundary.

It does not automatically include a PostgreSQL transaction, a payment provider or an email. Naming an external API call inside your transactional method does not make it part of Kafka's transaction. Explain this boundary in an interview before saying “exactly once.”

`KafkaExercise.java` commits `created`, aborts `aborted-payment`, then commits `approved` in one partition. After a broker restart, the reader must see only `created` and `approved`, in order. It explicitly commits its offset and verifies a new consumer resumes beyond those records. Another stage checks two consumers receive distinct partition assignments.

## 8. Rebalances and slow consumers

Group membership changes can reassign partitions. A handler must stop acting on partitions it no longer owns and avoid committing offsets for unfinished work. Processing longer than the allowed poll interval can make a healthy process appear failed to the group. Moving work into an executor is not sufficient unless you track completion and ownership per partition.

Lag measures the distance between a consumer's position and the end of a partition. It is useful, but one large slow event and many small events can have very different time-to-catch-up at the same lag. Also measure age of the oldest unprocessed event, handler latency, rebalance rate and error rate.

## 9. Retries, poison events and dead letters

Classify failures. A temporary database outage can be retried with backoff. An event with an impossible schema will not improve after a thousand retries. A poison event can block an ordered partition if you insist on strict processing order. Sending it to a dead-letter topic restores progress but changes the completeness or ordering of downstream business processing.

A dead-letter record should preserve original event ID, source topic/partition/offset, schema version, failure category and retry history. Avoid copying secrets unnecessarily. Replay is an operational change: repair the cause, retain the original business idempotency key, and monitor the result.

## 10. Schema evolution and event time

An event is a contract. Include event ID, event type, schema version, occurrence time, aggregate ID and payload. Add optional fields with defined defaults before removing or changing existing ones. A schema registry can enforce compatibility rules, but it cannot prove that a renamed amount field still means the same currency unit.

Event time is when the business action occurred; processing time is when your system handled it. Windowed processing needs a policy for late events, clock errors and corrections. Watermarks and grace periods express a lateness policy; they do not stop a source from sending older data later.

## 11. Outbox, CDC, Connect and Streams

The database outbox solves the gap between a business commit and event publication. A relay or change-data-capture connector publishes committed outbox rows. CDC reads changes from a database's change stream or log; operate it with permissions, retention and recovery in mind. Kafka Connect runs connectors and their offset/configuration infrastructure. Kafka Streams is a Java library for stateful stream processing, including joins, windows and local state stores backed by changelog topics.

Use simple producers and consumers first. Adopt these tools when their operational model fits the problem; a new component adds an upgrade, monitoring and failure responsibility.

## 12. Spring Boot and interview practice

In Spring applications, `KafkaTemplate` sends records and `@KafkaListener` methods receive them. Configure serializers, group ID, acknowledgment/error handling and transaction boundaries explicitly. Do not assume that `@Transactional` automatically combines every database and messaging operation into one atomic commit. An outbox usually makes the boundary easier to reason about.

Interview: “We have 12 consumers and six partitions. Why are six idle?” Explain partition ownership and distinguish groups. Follow-up: adding partitions may alter key routing. Interview: “The email was sent twice although producer idempotence was enabled.” Explain consumer redelivery and the external-effect boundary. Timed design: preserve per-order processing while scaling across many orders; name your key, partition strategy, retry policy and migration plan.

Reference provenance: [Kafka 4.1 quickstart and linked configuration documentation](https://kafka.apache.org/41/getting-started/quickstart/). The project and explanations here are self-contained; links document API provenance.
