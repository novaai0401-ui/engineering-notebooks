# Notebook 31 — Java, Spring Batch and microservices interview masterclass

This notebook answers every question in your supplied interview list. Start with the story, explain the mechanism, run the example, then attempt the follow-up without looking. The examples describe a payment-and-settlement learning system; they are not claims about your employment history. Java notebook cells need JDK 21 or later and Python. The separate Maven workshop exercises actual Spring transactions, Spring Batch, JUnit and Mockito.

## 1. Tell me about yourself and describe your experience

Think of an introduction as the label on a toolbox: tell the interviewer what problems you can solve, then show one useful tool. Aim for 60–90 seconds: current background, relevant skills, one concrete project, your contribution, one measured outcome, and why this role fits.

Template: “I am [your actual role/background]. I focus on [two relevant skills]. In [real project or explicitly named learning lab], I implemented [specific feature]. A difficult issue was [failure]; I diagnosed it using [evidence] and changed [implementation]. We verified [actual result]. I am now looking for [relevant responsibility].” Replace every bracket with something you can defend. Say “local learning project” when that is what you did.

For “Which databases have you worked on?”, separate production work, personal projects and theoretical knowledge. Example structure: “I used [engine/version] for [workload], wrote [queries/migrations], investigated [plan/locking issue], and verified [result]. I have studied Oracle plan analysis but have not operated Oracle in production.” Do not say you ran MySQL or Oracle because you ran the SQLite exercise below.

For “Have you implemented multithreading?”, describe the task split, shared state, synchronization, executor lifecycle, backpressure, cancellation and failure handling. For cloud experience, name only services you actually used and explain identity, networking, state, monitoring and costs. The library's local K3s deployment is Kubernetes experience in a local lab, not AWS/Azure/GCP production experience.

Follow-up drill: explain one failure you personally reproduced. If your story has no inputs, measurements or tradeoff, make it more concrete before memorizing it.

## 2. HashMap: numbered drawers with labelled cards

Imagine drawers containing customer cards. A hash chooses a drawer; equals identifies the correct card inside it. A collision means different keys choose the same drawer, not that one customer automatically overwrites another.

HashMap stores an array of buckets. In OpenJDK 21, buckets contain linked nodes or, for sufficiently crowded eligible buckets, red-black tree nodes. The implementation spreads the hash and uses the table size to select a bucket. For insertion it checks existing keys: an equal key replaces its value; an unequal colliding key gets a separate entry. Growth redistributes entries. Treeification constants and the minimum-capacity gate are implementation details, not the Map interface contract. Avoid the misleading claim “the eighth collision always creates a tree.” Tree bins also do not guarantee logarithmic lookup for every pathological non-orderable equal-hash key set. [OpenJDK implementation](https://raw.githubusercontent.com/openjdk/jdk21u/master/src/java.base/share/classes/java/util/HashMap.java).

Expected get/put cost is constant with suitable hash distribution; resizing and poor distribution affect actual cost. Default load factor is 0.75. HashMap allows a null key and null values, does not promise ordering, and is not thread-safe. A fail-fast iterator is a bug detector, not synchronization. [Java HashMap contract](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html).

**Interview answer:** “An array of buckets locates candidate entries by hash; equality selects the key. Modern OpenJDK can use tree bins for crowded buckets. Colliding but unequal keys coexist.”

```java
// lab: CollisionCards
import java.util.*;
public class CollisionCards {
  record Key(int id) { @Override public int hashCode() { return 7; } }
  public static void main(String[] args) {
    Map<Key,String> cards = new HashMap<>();
    cards.put(new Key(1), "Alice");
    cards.put(new Key(2), "Bob");
    assert cards.size() == 2;
    assert cards.get(new Key(1)).equals("Alice");
    cards.put(new Key(1), "Alicia");
    assert cards.size() == 2;
    assert cards.get(new Key(1)).equals("Alicia");
    System.out.println("Unequal colliding keys coexist; equal keys replace values.");
  }
}
```

Predict the size before running: two. The record supplies equality based on id; the deliberately constant hash slows lookup but does not break the equality contract. An interview follow-up may ask why HashMap is a poor choice when sorted keys or concurrent mutation are required: use a suitable ordered or concurrent map, not a promise the original map never made.

## 3. equals and hashCode: two parts of one address system

equals describes logical equality. hashCode helps hash-based collections find candidates. Equal objects must have equal hash codes; equal hash codes do not prove equality. Equality should be reflexive, symmetric, transitive, consistent and false for null. Override both methods from the same stable fields, or use a suitable immutable record.

If you override equals but inherit Object.hashCode, two logically equal instances may land in different buckets. HashMap lookup can fail or contain apparently duplicate logical keys. It is not guaranteed to fail on every run: accidental equal hashes may mask the defect. A test that happens to pass is not proof of a valid contract.

Mutable keys are another trap. Put a key into a map, change the field used for its hash, then look it up: the key's new address differs from its stored bucket. Prefer immutable identifiers, such as an account ID, over a mutable account balance. Do not use approximate floating-point comparison as equality for hash keys without a consistent canonical representation.

Exercise: two employees share a name but have different employee IDs. Should equals compare names? Usually not: a display label is not identity. State the domain rule before generating methods in the IDE. [Object equality/hash contract](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html).

## 4. Abstract classes, main and exception cleanup

An abstract class is a partly built machine. It can hold fields, constructors and implemented methods, and can require subclasses to implement abstract methods. You cannot instantiate it directly. It can have a static main method: launching that method does not require constructing the abstract class.

finally is not compulsory. A regular try needs a catch or finally; try-with-resources can appear without either. finally normally executes as control leaves the try/catch, including return or throw, but not after every possible JVM/process termination. Do not return from finally: it can hide an earlier result or exception.

Try-with-resources closes AutoCloseable resources in reverse declaration order. If the body and close both fail, the body's exception remains primary and the close failure is suppressed. This is useful for files, database connections and streams. It does not automatically make business work transactional. [Java resource handling](https://docs.oracle.com/javase/tutorial/essential/exceptions/tryResourceClose.html).

```java
// lab: CleanupStory
public abstract class CleanupStory {
  abstract String describe();
  static class Resource implements AutoCloseable {
    public void close() { throw new IllegalStateException("close failure"); }
  }
  public static void main(String[] args) {
    try (var resource = new Resource()) {
      throw new IllegalArgumentException("body failure");
    } catch (IllegalArgumentException error) {
      assert error.getMessage().equals("body failure");
      assert error.getSuppressed().length == 1;
      System.out.println("Abstract main ran; body failure retained; close failure suppressed.");
    }
  }
}
```

Follow-up: “Why not catch Exception and return null everywhere?” Because callers cannot distinguish missing data from failed work; observability and recovery become unreliable. Catch where you can recover or translate meaningfully, and preserve the cause.

## 5. Java 8 functional interfaces and employee filtering

A functional interface describes one job that a lambda can perform. It has one abstract method contract; compatible inherited methods can represent that same contract. Public Object methods do not count. Default and static methods do not add abstract jobs. @FunctionalInterface asks the compiler to enforce the rule, but the annotation is not required. [FunctionalInterface documentation](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/FunctionalInterface.html).

| Interface | Small story | Signature shape | Example |
| --- | --- | --- | --- |
| Predicate<T> | Gatekeeper says yes/no | T → boolean | Employee older than 40 |
| Function<T,R> | Converter | T → R | Employee → name |
| Consumer<T> | Uses an item | T → void | Write a record |
| Supplier<T> | Factory | () → T | Create a request ID |
| UnaryOperator<T> | Same-type transformation | T → T | Normalize a string |
| BinaryOperator<T> | Combine two same-type inputs | (T,T) → T | Combine totals |

```java
// lab: EmployeePredicates
import java.util.*;
import java.util.function.*;
public class EmployeePredicates {
  record Employee(String name, int age) {}
  interface Named { String name(); } // Functional even without the annotation.
  public static void main(String[] args) {
    var people = List.of(new Employee("Asha",40), new Employee("Ravi",41));
    Predicate<Employee> olderThan40 = employee -> employee.age() > 40;
    var names = people.stream().filter(olderThan40).map(Employee::name).toList();
    assert names.equals(List.of("Ravi"));
    Named label = () -> "approved";
    assert label.name().equals("approved");
    System.out.println(names);
  }
}
```

The requested operation uses Predicate, not Consumer. Streams describe a pipeline; they are not automatically faster than loops. Intermediate operations are lazy until a terminal operation runs. Avoid side effects in parallel pipelines, and do not assume parallelStream gives the right thread-pool isolation for blocking service calls.

## 6. synchronized versus ReentrantLock

A lock is a bathroom key: one owner enters a critical section at a time. synchronized acquires the monitor associated with an object or class and releases it when the block exits, including exceptional exit. It is reentrant: the owning thread can enter again.

ReentrantLock makes ownership explicit. Choose it when you need timed tryLock, interruptible acquisition or multiple Condition queues. Always release after successful acquisition in finally. Fair mode can reduce barging but may reduce throughput and does not guarantee fair CPU scheduling; untimed tryLock has its own fairness caveat. Do not choose it because of an unconditional “faster” claim. [ReentrantLock contract](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html).

```java
// lab: SafeCounter
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
public class SafeCounter {
  static class Counter {
    private final ReentrantLock lock = new ReentrantLock();
    private int value;
    void increment() {
      lock.lock();
      try { value++; } finally { lock.unlock(); }
    }
    int value() {
      lock.lock();
      try { return value; } finally { lock.unlock(); }
    }
  }
  public static void main(String[] args) throws Exception {
    var counter = new Counter();
    var pool = Executors.newFixedThreadPool(4);
    try {
      var futures = new java.util.ArrayList<Future<?>>();
      for (int i=0;i<4;i++) futures.add(pool.submit(() -> {
        for (int j=0;j<1000;j++) counter.increment();
      }));
      for (var future : futures) future.get();
      assert counter.value() == 4000;
      System.out.println("4000 increments retained; task failures propagate through Future.get.");
    } finally { pool.shutdownNow(); }
  }
}
```

In a payment API, do not hold a JVM lock during a slow bank call. It increases contention and does not coordinate other application instances. Use a durable transaction/idempotency protocol for cross-instance correctness. A local counter test proves local synchronization, not distributed serialization.

## 7. ConcurrentHashMap, synchronizedMap, races and deadlocks

Collections.synchronizedMap wraps operations with a common monitor. Iteration must synchronize on the returned map, and multi-call read-modify-write logic needs one shared critical section. Modern ConcurrentHashMap supports concurrent access without a single whole-map lock for ordinary operations; retrievals generally do not block. It rejects null keys/values and has weakly consistent iteration. Use atomic operations such as compute, merge or putIfAbsent for single-key compound updates. It is not a multi-key transaction manager. Do not describe modern ConcurrentHashMap as necessarily using the old fixed-segment architecture. [ConcurrentHashMap contract](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html).

Race example: two threads read a stock count of one, both approve a purchase and both write zero. The final number looks plausible, but two items were sold. A thread-safe map does not make `get` followed by `put` atomic. In a database, an update like `UPDATE stock SET available=available-1 WHERE id=? AND available>0`, plus checking affected rows inside the right transaction, can enforce the invariant.

Deadlock example: transfer A→B locks account A then waits for B; transfer B→A locks B then waits for A. Neither can advance. Acquire account locks in a stable ID order, reduce lock duration, inspect thread dumps or database deadlock reports, and retry a rolled-back database transaction only under a bounded policy. A timeout limits waiting; it does not repair inconsistent partial work.

A race is incorrect behavior caused by ordering; a deadlock is a cycle of waiting. They are different failure modes. volatile gives visibility and ordering for a variable but does not make `balance++` atomic. CompletableFuture introduces asynchronous composition, not automatic cancellation of every underlying task. Bound executors/queues and measure saturation.

## 8. SOLID through one payment example

Imagine a school office. A cashier calculates fees, a ledger records them and a messenger sends receipts. Giving every duty to one person makes every policy change disturb everything else.

| Principle | Concrete design | What would violate it? |
| --- | --- | --- |
| Single Responsibility | FeePolicy calculates; Ledger persists; ReceiptSender delivers | One class changes for fee rules, SQL schema and email layout |
| Open/Closed | Add a FeePolicy implementation behind a stable interface | Edit a huge switch for every new fee scheme |
| Liskov Substitution | Every Ledger implementation honors documented save semantics | A subtype silently drops accepted entries |
| Interface Segregation | ReadOnlyLedger exposes reads without mutation | A report generator must depend on refund/delete operations |
| Dependency Inversion | PaymentService depends on Ledger and FeePolicy abstractions | Business logic constructs a concrete JDBC connection directly |

SRP means one coherent reason to change, not “one method per class.” A useful refactoring starts with tests of existing behavior, extracts fee calculation, injects a ledger interface, and keeps transaction coordination explicit in the application service. Do not scatter one business invariant across five classes merely to increase class count.

Composition means a service **has** a policy. Inheritance means a subtype **is usable as** the parent under its behavioral contract. Choose composition for independently changing behavior, such as fee policy plus notification channel. Use inheritance for a real substitutable hierarchy or a framework's intended extension point. A Square that forbids Rectangle's independent width/height updates breaks that mutable Rectangle contract; mathematical naming alone does not establish substitutability.

```java
// lab: ComposedFees
import java.math.BigDecimal;
public class ComposedFees {
  interface FeePolicy { BigDecimal fee(BigDecimal amount); }
  record Checkout(FeePolicy policy) {
    Checkout { java.util.Objects.requireNonNull(policy); }
    BigDecimal total(BigDecimal amount) {
      if (amount.signum()<0) throw new IllegalArgumentException("negative amount");
      return amount.add(policy.fee(amount));
    }
  }
  public static void main(String[] args) {
    var free = new Checkout(amount -> BigDecimal.ZERO);
    var flat = new Checkout(amount -> new BigDecimal("2.00"));
    assert free.total(new BigDecimal("10.00")).compareTo(new BigDecimal("10"))==0;
    assert flat.total(new BigDecimal("10.00")).compareTo(new BigDecimal("12"))==0;
    System.out.println("Fee behavior changes through composition; money uses decimal values.");
  }
}
```

## 9. Design patterns: choose a problem before a pattern

SOLID gives design principles; patterns give recurring solution structures. Neither is a requirement to add abstractions to every class. Notebook 13 contains executable implementations of all 23 classic GoF patterns; use this map to connect them to interview scenarios.

| Family | Patterns | How to recognize the need |
| --- | --- | --- |
| Creational | Factory Method, Abstract Factory, Builder, Prototype, Singleton | Construction varies, compatible families matter, configuration is complex, copying is useful, or one lifecycle-owned instance is required |
| Structural | Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy | Translate an API, separate independent variations, model trees, wrap behavior, simplify a subsystem, share immutable state, or mediate access |
| Behavioral | Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor | Route handlers, represent actions, evaluate a grammar, traverse, coordinate, capture state, notify, vary state/algorithm, share a skeleton, or add operations over a stable structure |

For the payment example: Strategy selects a fee algorithm; Adapter translates a bank API; Decorator adds metrics around a gateway; Factory creates the configured adapter; Command represents a durable payment request; State models authorized/captured/refunded transitions; Observer suggests notifications but needs durable messaging when loss is unacceptable. A Spring proxy can implement cross-cutting transaction interception. Spring singleton scope is one bean per relevant container definition, not one object across every JVM or a distributed lock.

When patterns make design worse: a Factory for one trivial constructor obscures code; a global Singleton hides dependencies and test state; Observer chains hide ordering and errors; Template Method inheritance couples subclasses to parent sequencing; a “retry Decorator” around a non-idempotent debit can duplicate money movement. State the alternative and the failure behavior, not just a pattern name.

Follow-up: Strategy versus State? Strategy selects an algorithm; State changes behavior according to lifecycle transitions. They may have similar class shapes but express different domain intent. Adapter versus Facade? Adapter makes one interface usable as another; Facade offers a simpler entry point to a subsystem.

## 10. Constructor injection and the Spring transaction proxy

Constructor injection is a visible shopping list: a class cannot be created without its required dependencies. It supports final fields and ordinary unit-test construction. Field injection hides requirements and encourages reflection-based setup. An optional dependency should be deliberately optional; avoid treating every missing dependency as acceptable. Circular constructor dependencies often reveal unclear ownership rather than a need to hide the cycle.

With normal Spring proxy-based transaction management, a caller invokes a managed proxy. The interceptor obtains or joins a transaction, calls the target, then commits or rolls back according to the rules. Default propagation is REQUIRED; unchecked exceptions normally trigger rollback, while checked exceptions need an appropriate rollback rule unless configuration changes that behavior. Catching an exception and returning normally can prevent the intended rollback. [Spring transactional annotations](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html).

Self-invocation bypasses that proxy boundary: `this.debit()` is an ordinary call on the target. Its @Transactional annotation does not start a new transaction in standard proxy mode. If an outer transaction already exists, the inner code may still participate in it, but its own REQUIRES_NEW or rollback settings are not newly intercepted. Move the operation to an injected collaborating bean or use TransactionTemplate for an explicit boundary. AspectJ weaving is a different model, not the default explanation.

The accompanying Maven test proves the distinction with H2: a direct call through the proxy rolls back an insert when the method throws; a nontransactional same-class caller reaches the method without interception and leaves its autocommitted insert. This is a controlled demonstration, not a recommendation to rely on autocommit in a money workflow.

Important follow-up: a local JDBC transaction does not atomically roll back a remote bank's HTTP request. That requires an explicit protocol such as idempotency, durable state transitions and reconciliation. Also, transaction context is not automatically carried into arbitrary new threads.

## 11. REST operations and idempotency in payment systems

Think of a request as handing in a numbered form. A retry should refer to the same form, not create another debit.

| Method | Intended use | Retry contract |
| --- | --- | --- |
| GET / HEAD | Read representation / headers | Safe and idempotent semantics; never use a read to trigger a debit |
| PUT | Replace the resource at a known URI | Idempotent intended effect; responses and incidental logs can differ |
| DELETE | Remove the addressed resource | Idempotent intended effect; a later response can be 404 |
| POST | Create or execute application-defined work | Not inherently idempotent; implement a durable key contract when needed |
| PATCH | Apply a partial change | Depends on the patch: “set status” differs from “increment balance” |

The HTTP terms describe intended method effects, not identical response bytes on every call. [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods).

For `POST /payments`, scope the idempotency key by authenticated principal/tenant and operation. Store a canonical request fingerprint, state and outcome under a unique constraint. Same key and same payload return the same logical operation; same key with a different amount is a conflict. Decide how long keys remain valid and what happens after retention. Do not use a process-local map as the only protection.

Within one database, transactionally reserve the key, apply the ledger mutation and write an outbox event. Concurrent duplicates must converge through the constraint and a defined pending/completed response. For an external bank, durably create the intent first, use the bank's supported idempotency contract, and reconcile ambiguous timeouts by operation ID. A crash after the remote charge but before recording its result is the critical gap. Never interpret a timeout as proof that the charge did not occur.

Use integer minor units when the currency model permits it, or decimal arithmetic with explicit currency/rounding rules. Authentication, amount validation, currency, account ownership, available funds, audit trail and reversals are separate concerns. This is a software design exercise, not a complete financial-control specification.

```python
# lab: DurablePaymentKeys
import sqlite3
db = sqlite3.connect(':memory:')
db.executescript('CREATE TABLE payments(tenant TEXT, request_key TEXT, cents INTEGER, PRIMARY KEY(tenant,request_key));')
def submit(tenant, key, cents):
    if type(cents) is not int or cents <= 0:
        raise ValueError('positive integer minor units required')
    with db:
        db.execute('INSERT OR IGNORE INTO payments VALUES(?,?,?)',(tenant,key,cents))
        stored=db.execute('SELECT cents FROM payments WHERE tenant=? AND request_key=?',(tenant,key)).fetchone()[0]
        if stored != cents:
            raise ValueError('idempotency payload conflict')
    return stored
assert submit('a','request-1',1250)==submit('a','request-1',1250)
try:
    submit('a','request-1',999)
except ValueError:
    pass
else:
    raise AssertionError('conflict accepted')
assert submit('b','request-1',999)==999
assert db.execute('SELECT COUNT(*) FROM payments').fetchone()[0]==2
db.close()
print('Tenant-scoped key replay and payload conflict verified in SQLite; no remote charge was made.')
```

This deliberately small cell validates key semantics, not simultaneous requests or an external bank. The existing Study Coach and real-time labs exercise concurrent duplicate requests and crash recovery separately.

## 12. Millions of records: pagination, lazy loading and exports

Do not send millions of database rows in one JSON response. Bound page size, select only required columns, authorize every query, impose timeouts and avoid expensive exact total counts unless needed. Streaming a huge response can reduce application buffering, but it still holds connections and consumes bandwidth; it is not automatically a good interactive API.

Offset pagination is simple: `ORDER BY created_at,id LIMIT 100 OFFSET 500000`. Deep offsets may scan/discard many rows; concurrent inserts/deletes can shift page boundaries. Keyset pagination uses the last seen ordered values as a bookmark. For ascending order, select rows after `(last_created_at,last_id)`. Always include a unique tie-breaker and a supporting index.

```sql
-- MySQL-style parameterized query; use JDBC bind parameters, not string interpolation.
SELECT id, created_at, amount_minor
FROM payments
WHERE tenant_id = ?
  AND (created_at > ? OR (created_at = ? AND id > ?))
ORDER BY created_at, id
LIMIT 101;
```

Return 100 and use the extra row to decide whether another page exists. An opaque cursor can encode the last tuple, filter/version and an expiry, signed to resist tampering. A signed cursor is not authorization: reapply tenant checks on every request. Changes to sort keys can still move rows across the bookmark. Stable exports may need an explicit snapshot/version policy, not merely a high-water ID.

```python
# lab: BookmarkPages
import sqlite3
db=sqlite3.connect(':memory:')
db.executescript('CREATE TABLE rows(id INTEGER PRIMARY KEY, created INTEGER); CREATE INDEX ix_created_id ON rows(created,id);')
db.executemany('INSERT INTO rows VALUES(?,?)',[(1,10),(2,10),(3,11),(4,11),(5,12)])
cursor=(-1,-1); seen=[]
while True:
    page=db.execute('SELECT created,id FROM rows WHERE created>? OR (created=? AND id>?) ORDER BY created,id LIMIT 2',(cursor[0],cursor[0],cursor[1])).fetchall()
    if not page: break
    seen.extend(row[1] for row in page);cursor=page[-1]
assert seen==[1,2,3,4,5]
db.close()
print('Bookmark includes a unique tie-breaker: every static-data row appears once.')
```

Browser lazy loading means fetching the next page when needed; ORM lazy loading means deferring a relationship query. They are different. Mapping each returned order to `order.customer.name` can cause N+1 database queries. Use suitable DTO projections, fetch strategies or batch fetching, then verify query counts. Be cautious combining collection fetch joins and pagination. For very large downloads, prefer an authorized asynchronous export job, durable status and an expiring download link, with retry and cleanup policies.

## 13. MySQL composite indexes: a sorted address book

An address book sorted by country, city, then name helps you find a country's entries or one city's names. It is less useful when you know only a name. A composite B-tree index similarly orders tuples. MySQL commonly uses leftmost prefixes: `(tenant_id,status,created_at,id)` supports relevant searches beginning with tenant_id, but is not equivalent to four independent indexes. Special optimizer paths can exist, so verify the chosen plan rather than saying later columns can never matter. [MySQL multiple-column indexes](https://dev.mysql.com/doc/refman/9.7/en/multiple-column-indexes.html).

Start with a real query and its frequency. Put useful equality constraints before the relevant range/order portion when that fits the workload. For `tenant_id=? AND status=? AND created_at>=? ORDER BY created_at,id`, the tuple above is a candidate. The first range may limit later columns' use as range bounds; later columns can still help filtering, ordering in applicable cases or covering. Column order is not simply “highest cardinality first.”

Indexes cost storage and write/maintenance work. A covering index includes needed values, but adding large payload columns can make it too expensive. InnoDB secondary indexes also carry the primary key. Keep statistics representative and consider data skew. A scan can be cheaper when the query needs much of the table. Do not force an index merely to make EXPLAIN look impressive.

MySQL diagnostic recipe, not executed against a MySQL server in this notebook:

```sql
CREATE INDEX ix_payment_lookup ON payments(tenant_id,status,created_at,id);
EXPLAIN SELECT id,created_at FROM payments
WHERE tenant_id=42 AND status='SETTLED' AND created_at >= '2026-01-01'
ORDER BY created_at,id LIMIT 100;
EXPLAIN ANALYZE SELECT id,created_at FROM payments
WHERE tenant_id=42 AND status='SETTLED' AND created_at >= '2026-01-01'
ORDER BY created_at,id LIMIT 100;
```

Inspect the selected key/access path, estimates, actual rows/loops and time on a supported server version. EXPLAIN ANALYZE executes the statement; use representative, safe SELECT workloads in an appropriate environment. Benchmark with realistic parameters and concurrency, not only a tiny empty table. [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html).

## 14. Oracle EXPLAIN PLAN versus the executed cursor

EXPLAIN PLAN asks the optimizer for a proposed plan without executing the target statement. It does not establish which child cursor, bind-sensitive plan or actual row counts your application used. DISPLAY_CURSOR examines a cached cursor's plan; execution statistics must have been collected to see actual rows. [Oracle DBMS_XPLAN](https://docs.oracle.com/database/121/ARPLS/d_xplan.htm).

Oracle diagnostic recipe; requires an Oracle schema, suitable privileges and matching version, and is not claimed executed here:

```sql
EXPLAIN PLAN FOR
SELECT id FROM payments WHERE tenant_id=42 AND status='SETTLED';
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY());

SELECT /*+ gather_plan_statistics */ id
FROM payments WHERE tenant_id=42 AND status='SETTLED';
-- Fetch the result fully; identify its SQL_ID and CHILD_NUMBER in your environment.
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(
  :sql_id, :child_number, 'ALLSTATS LAST +PREDICATE'));
```

Look for the specific index name, operations such as INDEX RANGE SCAN and TABLE ACCESS BY INDEX ROWID, predicate placement, estimated versus actual rows, starts, buffers and elapsed work. A large estimate error suggests skew, stale statistics or correlation issues. An index used poorly may be slower than a scan. Functions on indexed columns, implicit type conversion and low selectivity can change access choices. Bind the correct types and compare alternatives with evidence.

Interview answer: “I inspect the executed cursor and actual work, not just the existence of an index. EXPLAIN PLAN is a prediction; DISPLAY_CURSOR with collected statistics helps verify the actual execution.” For an Oracle composite index, test its workload-specific behavior rather than copying a MySQL plan format. Notebook 29 covers the broader SQL, isolation and database design foundations.

## 15. API versioning, security and access/refresh tokens

URL versioning (`/api/v1/payments`) is easy to see, route and document. Header/media-type versioning keeps the URI stable but requires clients, gateways, cache keys and observability to preserve the version header; set Vary appropriately where responses are cacheable. Version the external contract, not every internal implementation edit. Prefer compatible additive changes when clients tolerate them, publish deprecation/migration windows, and test old/new consumers.

In Spring MVC, separate controller mappings can use paths or header conditions. For example, `@GetMapping(path="/payments", headers="X-API-Version=1")` selects a versioned handler. Do not create overlapping mappings that are ambiguous for a request. Newer framework versioning facilities are version-dependent; the explicit mapping example is easier to reason about across versions. [Spring request mapping](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-requestmapping.html).

Secure a REST API with TLS, validated identity, endpoint and object-level authorization, input validation, bounded payloads, rate limits, safe error handling and auditable outcomes. In an OAuth2 resource server, validate token signature with trusted keys, permitted algorithms, issuer, audience and time claims. Do not trust a decoded JWT merely because it is parseable. Enforce tenant/account ownership in service/data access, not only in the UI. [Spring resource-server validation](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html).

An access token authorizes API access for a limited period. A refresh token is presented to the authorization server to obtain new access tokens; it is not the normal credential sent to a resource API. Access tokens may be JWTs or opaque; refresh tokens need not be JWTs. Rotation, secure storage, reuse detection and revocation policy matter. A signed JWT is not encrypted, and logout does not instantly invalidate every previously issued self-contained access token without an additional design.

In a browser, HttpOnly cookies reduce script access but still require a suitable CSRF strategy. CORS controls browser cross-origin access, not authentication. Avoid putting tokens in logs or URLs. Short access-token lifetimes limit exposure; refresh-token lifecycle and compromised-session response remain necessary. The existing identity lab shows real OIDC logout boundaries and their limits.

## 16. Spring Batch: boxes of records and restart bookmarks

A batch job is a planned sequence of steps. A chunk step reads items, optionally processes them, and writes a group under a transaction. With chunk size two, five valid inputs normally produce commits for 1–2, 3–4, then 5. Larger chunks can improve throughput but hold more work/locks and increase replay after failure. Tune with realistic payloads. [Spring Batch 5.2 chunk configuration](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/configuring.html).

JobRepository records execution metadata. A JobInstance is identified by job name plus identifying parameters; each attempt is a JobExecution, with StepExecutions recording step attempts. Restart a failed instance using the same identifying parameters and preserved repository state. Adding a fresh timestamp often creates a new instance and defeats the intended restart. A completed instance ordinarily cannot simply run again with identical identity. ExecutionContext stores restart state for cooperating stateful components. [Spring Batch restart configuration](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/restart.html).

The runnable Maven workshop pins Spring Batch 5.2.4 with Spring Framework 6.2.12, separately from the library's Boot 4 application. A FlatFileItemReader saves its position. The writer fails on item 3 after inserting it. The failed chunk rolls back; rows 1 and 2 remain committed. Restarting the same job instance reprocesses the uncommitted chunk and ultimately leaves exactly rows 1–5. The test checks failure, checkpointed progress, restart identity and final row count. It uses an actual H2 database and Spring Batch metadata, not a handwritten imitation.

| Outcome | Example | Correct policy |
| --- | --- | --- |
| Filter | Valid row intentionally not eligible | Processor returns null; track as filtered |
| Skip | Malformed row the business explicitly permits quarantining | Narrow exception type, skip limit, reason and reconciliation |
| Retry | Transient deadlock/temporary failure | Bounded attempts/backoff and safe repeatable work |
| Fail | Corrupt source, exhausted retries or unsafe payment state | Stop and repair/reconcile before restart |

Skip is not “ignore everything”; a settlement job cannot silently discard money records and still call itself successful. Reader, processor and writer failures can have different transaction/replay implications. Record reject counts and compare source totals against accepted, filtered and rejected items. Validate the source's identity/checksum so a restart does not read a changed file at an old offset. [Skip configuration](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/configuring-skip.html), [retry configuration](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/retry-logic.html).

A chunk rollback cannot un-send email or undo a successful remote debit. Use transactional database state plus an outbox, provider idempotency and reconciliation for external effects. Partitioning assigns disjoint work units; multi-threaded steps require thread-safe or appropriately scoped components and careful ordering. Restartability is not exactly-once external execution. The test intentionally uses one thread and a stable input file; process-kill and distributed-partition recovery are distinct tests.

## 17. Microservice boundaries and data ownership

Imagine several school offices: admissions owns student enrolment, the cashier owns payments and the library owns book loans. Each office publishes a clear service contract. If everyone edits everyone else's records, dividing the rooms does not create independent ownership.

Decompose around cohesive business capabilities and bounded contexts, not one HTTP controller per service. Define ownership of invariants first. A modular monolith is often simpler while boundaries are uncertain. Microservices introduce network failure, operational overhead and consistency tradeoffs; they are not an automatic scalability upgrade.

| Pattern | Payment-system example | When it hurts |
| --- | --- | --- |
| Database per service | Ledger owns ledger writes; orders use a contract/event | Cross-service SQL shortcuts recreate coupling |
| API gateway | Route, authenticate and apply shared limits | Putting all business logic there creates a new monolith |
| Backend for frontend | Mobile endpoint composes only needed data | Too many nearly identical BFFs multiply maintenance |
| Service discovery | Find current payment service endpoints | Treating discovery as proof an instance is healthy |
| Strangler migration | Route selected old endpoints to a new service gradually | Permanent duplicate sources of truth |
| Anti-corruption layer | Translate legacy bank codes into internal domain terms | Hiding unhandled legacy semantics behind superficial renaming |
| API composition | Assemble order plus payment status on demand | Cascading latency and partial failures |
| CQRS | Write model protects invariants; read model optimizes dashboards | Extra models and eventual consistency without a real need |
| Event sourcing | Store domain events and rebuild state | Schema evolution, replay and privacy complexity; not required by CQRS |

Database-per-service means ownership and access boundaries; it does not necessarily require a separate physical database machine for each service. Never let a dashboard's eventually consistent projection become the authoritative source for whether funds are available.

## 18. Saga, outbox and idempotent consumer: connect the dots

A Saga coordinates local transactions with recovery actions. For an order: reserve stock, authorize payment, confirm order. If confirmation cannot complete, compensation might release stock and void authorization. Compensation is a new business action, not a time machine that guarantees restoration of every external effect. Captured money may require a refund with its own failure path.

Choreography lets services react to events; it reduces central coordination but can hide cycles and lifecycle ownership. Orchestration uses an explicit coordinator and durable state; it makes progress visible but needs its own recovery design. Choose based on the workflow's complexity and responsibility boundaries.

Outbox solves a specific dual-write gap. Save the local state change and outgoing event in one database transaction. A relay publishes later; it may publish twice after a crash. An inbox/deduplication record on the receiving side, committed with the business effect, makes duplicate handling safe. A unique event ID alone is insufficient unless its check and effect share the required atomic boundary.

```python
# lab: InboxReplay
import sqlite3
db=sqlite3.connect(':memory:')
db.executescript('CREATE TABLE inbox(id TEXT PRIMARY KEY); CREATE TABLE tally(value INTEGER); INSERT INTO tally VALUES(0);')
def consume(event_id, fail=False):
    with db:
        inserted=db.execute('INSERT OR IGNORE INTO inbox VALUES(?)',(event_id,)).rowcount
        if not inserted: return False
        db.execute('UPDATE tally SET value=value+1')
        if fail: raise RuntimeError('simulated crash before commit')
    return True
try: consume('event-1',True)
except RuntimeError: pass
assert db.execute('SELECT COUNT(*) FROM inbox').fetchone()[0]==0
assert consume('event-1') is True
assert consume('event-1') is False
assert db.execute('SELECT value FROM tally').fetchone()[0]==1
db.close()
print('Business update and dedup marker roll back together, then replay applies once.')
```

Complete request flow: authenticated client → gateway → order API with idempotency key → local order/outbox commit → relay → broker → payment inbox/local intent commit → bank call with provider idempotency key → durable outcome → Saga transition → read projection → SSE status update. Every arrow crossing a process can fail or deliver late. Trace IDs help observation; idempotency/event IDs protect business semantics and should not be confused with trace IDs.

Kafka transaction guarantees do not automatically encompass an arbitrary external bank request. Store ordering/version information for each aggregate when necessary, reject or reconcile stale transitions, and define how a dead-letter item returns to the normal flow after repair.

## 19. Resilience patterns and failure budgets

| Pattern | Child-friendly idea | Implementation question |
| --- | --- | --- |
| Timeout/deadline | Stop waiting for a bus after a limit | Does one end-to-end deadline constrain every downstream call? |
| Retry with jitter | Try again after different short waits | Is the operation safe to repeat, and which errors are transient? |
| Circuit breaker | Stop knocking on a broken door | What opens it, and how many half-open probes are allowed? |
| Bulkhead | Separate ship compartments | Are threads, connections and queues bounded per dependency? |
| Rate limit | Admit only a bounded arrival rate | Is fairness per user/tenant, and is Retry-After meaningful? |
| Load shedding | Reject work before collapse | Which work can be safely rejected and retried? |
| Cache-aside | Check the desk copy before the archive | What are TTL, invalidation, ownership and stale-data rules? |
| Backpressure | Slow the producer when the consumer fills | Is the buffer actually bounded, and can producers obey? |

Retries at three nested layers with three attempts each can produce 27 downstream attempts for one request. Give one layer clear retry ownership, propagate deadlines and use bounded exponential backoff with jitter. A circuit breaker is not a timeout and does not stop every already-running call. A fallback must not invent a successful payment; return pending/unavailable or a clearly labelled stale read when the contract permits it.

For readiness, ask whether an instance should receive traffic. For liveness, ask whether restarting it is likely to help. If a shared bank outage makes every pod fail liveness, restarting all pods creates more load without repairing the bank. Graceful shutdown should stop new work, drain or checkpoint safely and release leases predictably. Trace latency, saturation, error rates and business reconciliation gaps, not only CPU.

## 20. Kubernetes secrets and cloud interview answers

Never bake credentials into an image, source file or Docker ARG/ENV layer. Image layers can retain historical content. Supply runtime configuration through an appropriately protected Secret or an external secret manager integration, using workload identity where possible. Base64 in a Secret manifest is encoding, not encryption. Restrict RBAC, protect etcd storage, avoid secret logging and plan rotation. [Kubernetes secret practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/).

Mounted Secret files can be updated eventually; the application must reload them correctly. Environment variables in a running process do not automatically refresh when the Secret changes. A subPath mount has different update behavior. Rotation requires overlap/cutover rules and revocation, not just editing a YAML value. Separate build credentials from runtime application credentials, and do not commit populated Secret manifests.

Answer structure for cloud questions: “I deployed [actual workload] using [actual services]. Traffic entered through [route/TLS]. Workload identity permitted [scope]. State lived in [store]. We observed [metrics/logs], tested [failure] and controlled cost using [actual mechanism].” If you only ran this library, describe the local Docker/K3s topology and explicitly distinguish it from a managed-cloud deployment. The audit records that boundary.

Mini incident: after rotating a database password, half the pods fail. Investigate running process configuration, connection-pool reconnection, provider overlap rules and rollout readiness. Do not assume the Secret object's latest value is already the value every process uses.

## 21. JUnit, Mockito and automation testing

A unit test is a small experiment: arrange an input and dependencies, act once, assert the important result. JUnit runs and reports the experiment. Mockito can replace a boundary with a controlled test double, stub an outcome and verify a meaningful interaction. A mocked repository does not test SQL, constraints or transaction rollback.

The Maven workshop includes a fee-calculating service with constructor-injected Ledger. Its Mockito test checks the calculated amount and exactly one save; invalid input must cause no ledger interaction. The transaction test starts a real Spring context and H2 database. The batch test uses real Spring Batch metadata and a restartable reader. These layers answer different questions.

Test money edge cases, payload conflicts, duplicate requests, rollback, lock ordering, exhausted retry, authorization and empty pages. Use assertThrows for the intended exception; do not merely catch and ignore any exception. Prefer deterministic coordination such as latches/barriers over arbitrary sleeps in concurrency tests. Check failure propagation from submitted tasks.

Automation includes unit tests, database integration tests, API/consumer-contract tests, browser journeys, accessibility checks, performance/recovery scenarios and CI. Contract tests catch incompatible interfaces but do not prove the whole workflow works. Browser tests cover selected journeys but are slower and more fragile than focused tests. Keep clocks, IDs and dependencies controllable where that improves reproducibility. Testcontainers needs a working container engine; do not silently substitute H2 and claim MySQL/Oracle behavior was tested.

Run the actual workshop from the library root:

```shell
mvn -f labs/interview-workshop/pom.xml test
python run_notebook_labs.py --book 31-java-microservices-interview-masterclass
```

The first command needs Java 21+, Maven and initial dependency downloads. The second needs Python plus JDK tools for Java cells. The chapter's MySQL/Oracle commands remain labelled diagnostic recipes; the executed database tests use H2 and SQLite.

## 22. Sprint Retrospective and a graded interview round

A Sprint Retrospective is the team's inspection of how the Sprint went and how to improve effectiveness and quality. Discuss interactions, process, tools, assumptions and the Definition of Done, then choose actionable improvements. It is different from the Sprint Review, which inspects the product outcome with stakeholders and adapts future direction. It is not a blame meeting or merely a status update. [Scrum Guide](https://scrumguides.org/scrum-guide.html).

Example: repeated flaky browser tests delayed releases. Bring failure evidence, identify uncontrolled clocks, agree to inject a clock into the affected feature, assign an owner and check the result next Sprint. “Communicate better” without an action or observation is hard to evaluate. Teams should make it safe to discuss mistakes while still assigning concrete follow-through.

Attempt this 45-minute round without the answers: ten minutes on HashMap/equality and employee filtering, ten on lock choice and transaction self-invocation, fifteen designing a payment POST plus paginated GET, and ten on Batch restart, index verification and one retrospective action.

| Question / follow-up | Answer key essentials | Points |
| --- | --- | --- |
| Colliding keys, equal keys and mutable keys | Collision is not equality; equal keys replace; equality/hash contract; mutation can break lookup | 4 |
| Filter employees older than 40 | Predicate<Employee>, strict greater-than, boundary at 40 | 2 |
| Lock and map choice | Proper finally unlock, single-key atomic operations, no distributed-lock claim | 3 |
| Transaction self-invocation | Proxy boundary bypass; outer transaction nuance; collaborator/TransactionTemplate repair | 4 |
| Payment retry after lost response | Tenant-scoped durable key, fingerprint, unique constraint, ambiguous remote result, reconciliation | 5 |
| Huge GET and indexes | Bounded keyset page, unique tie-breaker, authorization, query-specific index and actual plan | 4 |
| Batch failure on record 3 | Committed chunk retained, failed chunk rolled back, same instance parameters, checkpoint and stable input | 4 |
| Microservice failure flow | Outbox duplicates, transactional inbox, Saga compensation limits, bounded retries | 2 |
| Retrospective | Process inspection, concrete improvement, distinction from Review | 2 |

Total 30. Suggested practice target: 24, with no claim that a timeout proves a payment failed or that a local transaction undoes a remote debit. Any such error needs correction regardless of total. Explain why your design works, how it fails and how you would test it. Your personal grade remains unset until you submit unaided answers and elapsed time.

## 23. Question coverage and next study links

| Supplied interview area | Where answered here | Existing deeper notebook |
| --- | --- | --- |
| Introduction and experience | Lesson 1 | [Interview practice](15-interview-practice.html) |
| HashMap, collisions, equals/hashCode | Lessons 2–3 | [Java foundations](03-java-spring-boot.html) |
| Abstract class/main, try/finally/resources | Lesson 4 | [Java depth](10-java-spring-depth.html) |
| Functional interfaces, annotation, Predicate | Lesson 5 | [Java foundations](03-java-spring-boot.html) |
| synchronized/locks, concurrent maps, race/deadlock | Lessons 6–7 | [Java depth](10-java-spring-depth.html) |
| SOLID, SRP, composition/inheritance, design patterns | Lessons 8–9 | [All 23 GoF implementations](13-patterns-workshop.html) |
| Injection, transaction internals/self-invocation | Lesson 10 | [Full-stack workshop](14-fullstack-workshop.html) |
| HTTP/idempotency and millions of GET records | Lessons 11–12 | [Database foundations](29-databases-for-fullstack-and-ai.html) |
| Composite indexes, MySQL/Oracle plans | Lessons 13–14 | [Databases](29-databases-for-fullstack-and-ai.html) |
| API versions, API security, access/refresh tokens | Lesson 15 | [Identity and deployment](17-identity-and-deployment.html) |
| Batch chunks, restartability, error handling | Lesson 16 and Maven workshop | [Recovery and operations](27-reliability-evaluation-and-operations.html) |
| Microservice patterns and connected architecture | Lessons 17–19 | [Distributed systems](18-distributed-systems-lab.html) |
| Kubernetes secrets and cloud experience | Lesson 20 | [Kubernetes](24-kubernetes-from-pods-to-recovery.html) |
| JUnit, Mockito, automation and retrospective | Lessons 21–22 | [Capstone assessment](28-fullstack-capstone-and-assessment.html) |

Reference checks were performed on 25 September 2026. Linked official sources are optional verification material; the teaching explanations, examples and answer keys are included in this notebook. Exact framework pins and executed results are recorded in the workshop, while provider-specific recipes and personal experience remain explicitly distinguished.
