# Notebook 10 — Java and Spring beyond the happy path

A Java service is like a busy school office. Objects hold records, threads are clerks, the database is the official register, transactions protect related changes, and security checks who may request them. Faster clerks cannot repair a broken register contract. This notebook connects language rules to measurable service behavior.

## 1. JVM memory and garbage collection

Each thread has a stack of call frames, including local variables and references. Objects generally live on the heap, subject to runtime optimizations. Class metadata uses metaspace; native libraries, direct buffers, thread stacks and code caches also consume memory. `-Xmx` limits the Java heap, not total process memory. An out-of-memory failure can therefore occur even when a heap chart looks comfortable.

Garbage collection identifies unreachable objects; it does not mean “delete an object immediately after its last visible use.” A static map retaining every request can keep objects reachable forever. Closing a database connection or file is a resource-lifetime responsibility, not a job to leave to the collector. Use try-with-resources for `AutoCloseable` objects.

Different collectors and configurations trade throughput, pause times and memory. Begin with workload evidence rather than memorizing one universal best collector. Record allocation rate, live heap after collection, pause distribution, CPU and request latency. Use JVM tools such as Java Flight Recorder, `jcmd`, and GC logs with appropriate permissions. A heap dump may contain credentials and user data; handle it as sensitive data.

**Worked diagnosis:** Heap use rises during each batch and returns to roughly the same baseline after collection: likely allocation pressure. The post-collection baseline rises steadily with retained request entries: suspect retention. CPU is idle but latency is high and all workers await connections: investigate a saturated connection pool, not only GC.

## 2. Generics, variance, and erasure

A `List<Integer>` is not a `List<Number>`: if it were, a caller could add a `Double` into the integer list. A producer that gives you numbers can use `? extends Number`; a consumer that accepts integers can use `? super Integer`. This is the idea behind “producer extends, consumer super.” Type erasure means most generic type arguments are unavailable as ordinary runtime class distinctions; do not use unchecked casts as a substitute for validation.

```java
// lab: GenericTransfer
import java.util.*;
public class GenericTransfer {
 static <T> void copy(List<? extends T> source,List<? super T> target){
  for(T value:source)target.add(value);
 }
 static double total(List<? extends Number> values){
  return values.stream().mapToDouble(Number::doubleValue).sum();
 }
 public static void main(String[] args){
  List<Integer> integers=List.of(1,2,3);
  List<Number> numbers=new ArrayList<>();copy(integers,numbers);
  assert total(numbers)==6;
  System.out.println("A producer of integers can feed a consumer of numbers");
 }
}
```

Use immutable records for value-like data when their members support the intended immutability. A record containing a mutable list is only shallowly immutable; defensively copy the list if needed. `equals` and `hashCode` must agree. Mutating a key field after inserting an object into a hash map can make lookup fail.

## 3. Concurrency: visibility, atomicity and ordering

`count++` reads, adds and writes; those operations are not one atomic action. `volatile` supplies visibility and ordering guarantees for the variable but does not turn arbitrary compound operations into transactions. Locks protect invariants involving several values. Atomic classes support specific atomic operations. A thread-safe collection does not automatically make “check then act” across several calls atomic.

```java
// lab: BoundedPipeline
import java.util.concurrent.*;
public class BoundedPipeline {
 public static void main(String[] args)throws Exception{
  BlockingQueue<Integer> queue=new ArrayBlockingQueue<>(2);
  try(var executor=Executors.newVirtualThreadPerTaskExecutor()){
   Future<Integer> consumer=executor.submit(()->{
    int sum=0;
    while(true){int value=queue.take();if(value==-1)return sum;sum+=value;}
   });
   Future<?> producer=executor.submit(()->{
    try{for(int i=1;i<=5;i++)queue.put(i);queue.put(-1);}
    catch(InterruptedException e){Thread.currentThread().interrupt();throw new RuntimeException(e);}
   });
   producer.get(2,TimeUnit.SECONDS);
   assert consumer.get(2,TimeUnit.SECONDS)==15;
  }
  System.out.println("A bounded queue applies backpressure between producer and consumer");
 }
}
```

The sentinel works because this example has one consumer and data never uses `-1`. Multiple consumers need a termination protocol suitable for their number, or explicit cancellation. Virtual threads make many blocking tasks cheaper than one platform thread per task; they do not create unlimited database connections, memory or remote capacity. Bound scarce resources separately.

Deadlock requires a cycle of waiting. Consistent lock ordering can prevent such cycles. Timeouts reduce indefinite waiting but require a safe recovery policy. On interruption, release resources and preserve or propagate the interrupt according to your API contract. Do not swallow it and continue expensive work.

## 4. Spring dependency injection and proxy behavior

Constructor injection makes required dependencies explicit and supports ordinary unit tests. The container creates and connects beans. A singleton bean is shared within the application context; it must not keep request-specific mutable fields. A controller field named `currentUser` is a cross-request bug, even if the first manual test succeeds.

Spring often applies features through proxies. In default proxy-based transaction management, a call from one method to another method on the same object can bypass transactional advice. Put the transaction boundary on a service method called through its managed bean. Read the [transaction annotation reference](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html) for proxy and rollback behavior. Configure rollback rules deliberately; do not assume every checked exception rolls back under every configuration.

Transactions should protect database invariants, not wrap a slow model call by default. Holding locks and connections while a remote model responds reduces capacity and increases contention. Commit a durable job first, then let a worker call the external service outside the short database transaction.

## 5. Isolation with a concrete race

Two clerks read that one seat remains. Both subtract one in their own memory and write zero. Both customers receive a seat. The final counter looks valid, but the business invariant was broken. Possible solutions include an atomic conditional update (`UPDATE ... SET seats=seats-1 WHERE seats>0`), optimistic version checks, row locking, or a stronger transaction design. Select according to contention, retry cost and database behavior.

Read committed generally prevents dirty reads. Repeatable read and serializable offer stronger guarantees, but exact behaviors and anomalies differ among database engines. Do not infer PostgreSQL or MySQL semantics from an H2 test alone. Serialization failures and deadlocks may require retrying the complete transaction, with bounded attempts and idempotent external behavior.

The Study Coach `PersistenceTests` uses two actual database connections to show that an uncommitted row is hidden at read committed and becomes visible after commit. It separately tests optimistic locking: two detached versions are loaded; one update wins and the stale version is rejected.

## 6. JPA performance: measure the SQL

JPA maps object operations onto SQL. Lazy loading delays a relationship query; eager loading requests early availability but does not guarantee one efficient SQL statement. The N+1 problem occurs when one query loads N parents and then one query per parent loads its children. In the classroom test, three courses produce four queries. A fetch join produces one query for the same small result.

`CourseRepository.withLessons()` uses a fetch join. `PersistenceTests.fetchJoinAvoidsNPlusOne` clears the persistence context and Hibernate statistics before each measurement, then asserts four versus one prepared statements. Without clearing the first-level cache, the second measurement could appear fast merely because the objects were already loaded.

Fetch joins are not universally free: joining large collections duplicates parent columns, can multiply rows across several collections, and complicates pagination. Alternatives include projections, entity graphs, batch fetching, and two-step ID pagination. Return API DTOs rather than exposing an arbitrary entity graph to JSON serialization. Open-session-in-view can hide missing query planning by triggering queries during rendering; this project disables it.

## 7. Messaging and the transactional outbox

Suppose you insert an enrollment and then publish a message. A crash between these steps leaves an enrollment with no event. Reversing the order can publish an event for a transaction that later rolls back. The outbox stores the business change and a pending event in the same database transaction. A separate relay publishes pending events.

The `Enrollment` service and its integration test show both records rolling back together on a deliberate exception, then both committing on success. This is the producer-side atomicity part of the pattern. The project does not include a Kafka or RabbitMQ broker. A production relay must handle claims, retries, duplicate publishing and ordering; consumers need idempotency because a relay can crash after publish but before marking delivery.

An event describes something that happened; a command requests an action. Choose schemas, partition keys and ordering requirements explicitly. A dead-letter queue is a holding area for investigation, not a way to declare lost work successful. Record why an item failed and how it may be replayed safely.

## 8. Cache correctness before cache speed

A cache stores a reusable result. Its key must include every input that affects the result, including identity or permission scope where relevant. Omitting the owner from a retrieval cache key can leak another user's data. Decide TTL, size bound, invalidation and behavior during a miss storm. Do not cache failures forever.

```java
// lab: ScopedCache
import java.util.*;
public class ScopedCache {
 record Key(String owner,String query){}
 record Entry(String value,long expires){}
 static class Cache {
  final Map<Key,Entry> entries=new LinkedHashMap<>();
  final int capacity;
  Cache(int capacity){if(capacity<1)throw new IllegalArgumentException();this.capacity=capacity;}
  synchronized void put(Key key,String value,long now,long ttl){
   entries.remove(key);entries.put(key,new Entry(value,now+ttl));
   while(entries.size()>capacity)entries.remove(entries.keySet().iterator().next());
  }
  synchronized Optional<String> get(Key key,long now){
   Entry item=entries.get(key);
   if(item==null)return Optional.empty();
   if(item.expires()<=now){entries.remove(key);return Optional.empty();}
   return Optional.of(item.value());
  }
  synchronized void invalidate(Key key){entries.remove(key);}
 }
 public static void main(String[] args){
  Cache cache=new Cache(2);Key alice=new Key("alice","plan");
  cache.put(alice,"private",0,10);
  assert cache.get(new Key("bob","plan"),1).isEmpty();
  assert cache.get(alice,10).isEmpty();
  cache.put(alice,"new",10,10);cache.invalidate(alice);
  assert cache.get(alice,11).isEmpty();
  System.out.println("Cache keys include owner; expiration and invalidation are tested");
 }
}
```

This small cache evicts by insertion order and synchronizes operations; it is not a distributed cache or a production caching library. For expensive loads, coalesce simultaneous misses. For updates, explain the ordering between commit and invalidation. Strong consistency requirements may make a cache inappropriate.

## 9. Security and integration tests

The connected application uses Spring Security, password hashing, HTTP Basic for the local teaching session, CSRF protection, owner-filtered database queries, and an internal service credential for Python. Basic credentials must travel over TLS beyond local development. They are not encryption. The browser page keeps its explicit authorization header in memory and does not store it in localStorage. Forgetting page credentials is not server-side session revocation.

Read [Spring's Basic authentication documentation](https://docs.spring.io/spring-security/reference/servlet/authentication/passwords/basic.html) for filter behavior. Test absent authentication, incorrect credentials, missing CSRF token, another user's job ID, malformed input and every state-changing endpoint. A controller unit test cannot establish these filters work; use integration and network tests as well.

## 10. Interview exercise and rubric

**Task, 20 points:** Design enrollment plus notification under concurrency. Award 4 points for the seat invariant and a valid atomic strategy, 3 for transaction boundaries, 3 for an outbox and idempotent consumer, 3 for JPA query planning, 3 for identity/ownership checks, and 4 for failure tests covering rollback, duplicate delivery and concurrent attempts.

**Follow-up:** Would `synchronized` on one service method solve double booking across three servers? No; its lock exists only in one JVM. **Follow-up:** Would adding `@Transactional` everywhere solve N+1? No; transaction scope and query shape are separate. **Follow-up:** Does a cache always improve latency? A remote cache, serialization overhead or a miss storm can make it worse. Measure the complete path.
