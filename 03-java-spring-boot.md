# Notebook 3 — Java and Spring Boot, From Objects to Services

This notebook builds from simple Java calculations to a layered HTTP service. The companion algorithms notebook contains the classic design-pattern catalog and algorithm practice. Here we apply those ideas to Java and Spring. Read the lessons offline. Running Java labs needs a JDK; running the Spring project additionally needs Maven and initially available dependencies.

## 1. Java is a typed recipe language

A variable has a declared type. A class describes objects and behavior. An object is one instance. A method is a function belonging to a class or object. The compiler translates source into bytecode; the JVM executes it using interpretation and/or runtime compilation. The JDK supplies development tools such as the compiler, not just execution support.

Primitive types include `int`, `long`, `double`, `boolean`, and `char`. Reference variables refer to objects or null. `String` represents text and is immutable. `final` prevents reassignment of a variable; it does not magically make a referenced mutable object's contents immutable.

```java
// lab: FirstJava
public class FirstJava {
    static int total(int count, int price, int fee) {
        if (count < 0) throw new IllegalArgumentException("negative count");
        return Math.addExact(Math.multiplyExact(count, price), fee);
    }
    public static void main(String[] args) {
        if (total(3, 10, 5) != 35) throw new AssertionError();
        String a = new String("book");
        String b = new String("book");
        if (!a.equals(b)) throw new AssertionError();
        System.out.println("Total: 35; text values equal");
    }
}
```

`public class` names the program. `static` makes a method callable without creating an instance. Exact arithmetic throws on overflow instead of silently wrapping. `main` is the entry point for this ordinary Java program. `equals` compares String values; `==` compares reference identity for objects. Compile using `javac FirstJava.java`, then run `java FirstJava`.

**Practice:** Does `final List<String>` prevent adding an item? **Answer:** No. It prevents changing that variable to refer to another list; the list's own mutability still matters.

## 2. Objects, interfaces, records, and encapsulation

Imagine different calculators following one agreement: each can quote a price. An interface expresses that agreement. Implementations supply behavior. Encapsulation protects an object's rules rather than exposing arbitrary writable fields.

```java
// lab: PricingDemo
public class PricingDemo {
    interface Pricing { int price(int quantity); }
    record FlatPricing(int unitPrice) implements Pricing {
        FlatPricing {
            if (unitPrice < 0) throw new IllegalArgumentException();
        }
        public int price(int quantity) {
            if (quantity < 0) throw new IllegalArgumentException();
            return Math.multiplyExact(unitPrice, quantity);
        }
    }
    static int checkout(Pricing pricing, int quantity) {
        return pricing.price(quantity);
    }
    public static void main(String[] args) {
        if (checkout(new FlatPricing(7), 3) != 21) throw new AssertionError();
        System.out.println("Strategy supplied through an interface");
    }
}
```

The interface names the capability. The record is a compact data carrier with generated accessors and value-oriented methods. Its constructor validates the rate. `checkout` depends on an abstraction rather than one concrete pricing class. This is composition and dependency injection in ordinary Java, without a framework.

Inheritance expresses an is-a relationship with substitutability constraints. Composition expresses has-a or uses-a. A subtype should preserve the contract expected by callers; throwing unsupported-operation errors for normal parent behavior may violate that expectation. Prefer narrow interfaces that callers actually need.

## 3. Collections, generics, equality, and hashing

An ArrayList provides indexed dynamic-array access. A linked list stores linked nodes; knowing a node can make local changes cheap, but finding an index is linear. A HashMap associates keys with values using hashes and equality. A TreeMap maintains ordered keys. A HashSet tests distinct membership; a priority queue exposes the smallest or comparator-preferred element, not a globally sorted iteration order.

Generics such as `List<String>` express element types and catch many errors at compilation. Java generics are largely implemented with type erasure; a generic parameter is not always available as runtime type information. A `List<Dog>` is not a `List<Animal>` because the latter could permit adding a Cat.

PECS means producer extends, consumer super: use suitable wildcard bounds when an API reads produced values or accepts consumed ones. Do not add wildcards everywhere; first identify the direction of use.

Equal objects must have equal hash codes. Mutating a key's equality-relevant fields after insertion can make hash-based lookup fail. Hash collisions are possible and do not imply equality. Arrays use identity-based equality unless you use appropriate array comparison utilities.

```java
// lab: CollectionDemo
import java.util.*;
public class CollectionDemo {
    public static void main(String[] args) {
        Map<String, Integer> counts = new HashMap<>();
        for (String word : List.of("ai", "java", "ai")) {
            counts.merge(word, 1, Integer::sum);
        }
        if (counts.get("ai") != 2) throw new AssertionError();
        List<String> ranked = counts.keySet().stream()
            .sorted(Comparator.comparingInt((String k) -> counts.get(k))
                .reversed().thenComparing(Comparator.naturalOrder()))
            .toList();
        if (!ranked.equals(List.of("ai", "java"))) throw new AssertionError();
        System.out.println(ranked);
    }
}
```

`merge` inserts one or combines with the old count. The stream builds a processing pipeline. The comparator sorts larger counts first and text as a tie-breaker. `toList` collects the stream result; do not assume every list-returning API promises mutability. Streams do not inherently improve speed or make side effects safe.

## 4. Exceptions, resources, and Optional

An exception is a structured failure path. Checked exceptions require declaration or handling; unchecked exceptions extend RuntimeException and typically represent programming or application failures not enforced at the signature. Do not use that distinction alone to decide whether a failure is recoverable.

Try-with-resources closes AutoCloseable resources. Preserve causes when wrapping errors. Avoid catch-all handlers that hide failure and return empty business results. A missing record and a failed database connection are different outcomes.

Optional expresses an explicitly optional return. It can reduce accidental null assumptions, but calling `get()` blindly recreates the problem. `orElse` evaluates its fallback eagerly; `orElseGet` calls a supplier when necessary. Null checks still matter at external boundaries.

Immutability makes sharing easier. Defensive copies protect collections. Records are shallowly immutable in their component bindings, not necessarily in nested data. Validate constructor invariants and avoid publishing partially initialized objects.

**Practice:** Why is returning an empty list for a database timeout misleading? **Answer:** Callers cannot distinguish no records from unavailable information and may take incorrect actions.

## 5. JVM, memory, and concurrency

Objects are generally managed on the heap; method frames and local execution state use thread stacks, subject to optimization details. Garbage collection reclaims unreachable managed objects; it does not guarantee immediate release of files or sockets. A memory leak can occur when reachable structures retain objects no longer needed.

Concurrency is overlapping progress. Parallelism is simultaneous execution. A race occurs when outcomes depend on uncontrolled interleaving. `volatile` supports visibility and ordering for a variable, but `count++` is a read-modify-write sequence and is not made atomic just by volatile.

```java
// lab: ConcurrentCount
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
public class ConcurrentCount {
    public static void main(String[] args) throws Exception {
        AtomicInteger count = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<?> a = pool.submit(() -> { for(int i=0;i<1000;i++) count.incrementAndGet(); });
            Future<?> b = pool.submit(() -> { for(int i=0;i<1000;i++) count.incrementAndGet(); });
            a.get(); b.get();
            if (count.get() != 2000) throw new AssertionError();
            System.out.println(count.get());
        } finally { pool.shutdown(); }
    }
}
```

The executor owns worker threads. Futures let the caller await completion and observe failures. AtomicInteger makes each increment atomic; it would not automatically protect a multi-variable business invariant. Always close or shut down owned execution resources.

Locks protect critical sections; consistent lock ordering helps avoid deadlock. CompletableFuture composes asynchronous results but needs deliberate executor and exception handling. Virtual threads can support many blocking tasks with lower per-thread overhead in suitable workloads; they do not make CPU work free, remove database limits, or provide backpressure automatically. [Java learning baseline](https://dev.java/learn/).

## 6. SOLID, cohesion, and boundaries

Single responsibility means grouping behavior that changes for the same reason. Open/closed means enabling expected extensions without repeated invasive edits. Liskov substitution means preserving the contract of an abstraction. Interface segregation means avoiding forcing clients to depend on unrelated methods. Dependency inversion means policy depends on abstractions, with concrete details supplied at boundaries.

Imagine a checkout service. It calculates a total, then asks a Payment interface to charge. A provider-specific SDK sits behind an adapter. This isolates the business rule from SDK changes. Do not create twenty interfaces for a one-function toy merely to claim architectural sophistication.

DRY avoids duplicated knowledge, not every repeated line. KISS prefers clear solutions. YAGNI avoids speculative features. High cohesion keeps related behavior together; low coupling limits unnecessary dependencies. Composition, explicit invariants, immutability, and clear error contracts often matter more than naming a design pattern.

The companion pattern notebook explains all 23 classic GoF patterns with concrete examples and cautions. In Spring you commonly encounter Factory, Proxy, Adapter, Strategy, Template Method, Observer-style events, and dependency injection, which is a broader construction technique rather than one of those 23 patterns.

## 7. Spring: a container assembles objects

In ordinary Java you write `new Service(repository)`. Spring can construct and connect managed objects, called beans. Inversion of control means the container controls this construction lifecycle. Dependency injection supplies what an object needs, often through its constructor.

`@Component` marks a discoverable component; service and repository stereotypes communicate roles. `@Configuration` and `@Bean` define objects explicitly. Constructor injection makes required dependencies visible and supports tests without container startup. Multiple candidates require qualification or a clear selection rule.

Singleton scope normally means one bean instance per application context, not a universal JVM or cluster singleton. Request scope ties lifecycle to a request. A singleton with mutable per-user fields can leak or mix concurrent requests. Keep request data in request-specific values, not shared service instance fields.

Spring Boot adds opinionated setup, dependency management, and conditional auto-configuration. Conditions inspect classes, existing beans, and configuration. Boot does not remove Spring's underlying object lifecycle. Inspect configuration rather than calling unexpected behavior “magic.”

## 8. A layered service

```text
HTTP request -> controller -> application service -> repository
                                  |                    |
                             domain rules          database
HTTP response <- response DTO <---+
```

A controller translates HTTP. The service coordinates a use case and its invariants. A repository handles persistence. DTOs define external data shapes. Domain objects express business concepts. An entity maps persistence; returning it directly can couple your API to storage and expose unwanted fields.

Hexagonal architecture calls external interfaces ports and concrete integrations adapters. A modular monolith can preserve these boundaries inside one deployment. Microservices add independently deployed boundaries and distributed failure; choose them for actual operational needs, not as a default interview decoration.

**Example:** `POST /reservations` accepts a book ID. The controller validates shape, the service verifies authority and availability, and the repository persists a reservation transactionally. An LLM recommendation does not bypass this path.

## 9. HTTP, validation, and error contracts

GET retrieves without intended mutation. POST commonly creates or initiates work. PUT represents replacement semantics at an identified resource and is intended to be idempotent. PATCH applies a partial change whose idempotency depends on the patch operation. DELETE is idempotent in intended effect even if repeated response codes differ.

Use status codes deliberately: 200 success, 201 created, 202 accepted for ongoing processing, 400 invalid request, 401 unauthenticated, 403 forbidden, 404 missing or intentionally undisclosed resource, 409 state conflict, 429 rate-limited, and 5xx server-side failure classes. Include stable error codes and request IDs without leaking stack traces.

Validate DTO fields with Bean Validation and enforce business invariants in services and databases. A “positive amount” annotation cannot verify that a user owns an account. Input type validation, authentication, authorization, and business validity solve different problems.

### Framework recipe: a small controller

The delivered `labs/spring-demo` project contains the complete build and testable controller. This excerpt is the teaching view, not an instruction to place every class into one file.

```java recipe
@RestController
@RequestMapping("/api")
class GreetingController {
    @GetMapping("/greeting")
    Greeting greeting(@RequestParam(defaultValue="learner") String name) {
        if (name.isBlank() || name.length() > 80) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid name");
        }
        return new Greeting("Hello, " + name);
    }
    record Greeting(String message) {}
}
```

The class handles HTTP requests. The mapping prefixes paths. The method reads a query parameter, checks a small constraint, and returns a structured record that the configured web stack serializes. It is a deliberately public demonstration greeting, not a template for exposing private data without authentication. [Official REST guide](https://spring.io/guides/gs/rest-service).

## 10. Transactions, JPA, and database correctness

A transaction groups changes under chosen guarantees. Atomicity means all-or-nothing within its boundary. Consistency means application/database invariants are preserved by correctly designed operations. Isolation controls what concurrent work can observe. Durability concerns committed changes surviving failures within the storage system's guarantees.

`@Transactional` commonly works through a proxy around bean calls. Self-invocation can bypass that proxy, so annotating a method does not guarantee every internal call starts the intended transaction. Defaults commonly roll back unchecked exceptions; checked-exception rollback and other behavior are configurable. Verify your transaction manager and framework configuration. [Official transaction semantics](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html).

JPA maps Java objects and relationships to persistent records. An EntityManager tracks managed entities within a persistence context. Dirty checking notices changes for flushing; flush synchronizes SQL work but is not identical to transaction commit. Lazy loading defers fetching and can fail outside the needed context. N+1 queries arise when loading a collection triggers an extra query per item.

Use explicit fetch plans, projections, or suitable joins for read paths. Index frequent predicates and join keys after examining query plans. Optimistic locking uses versions to reject conflicting updates; pessimistic locking holds database locks under defined scope. A Java synchronized block cannot coordinate independent service instances by itself.

**Practice:** Two users reserve the last copy simultaneously. What prevents double booking? **Answer:** A database-enforced constraint or correctly isolated conditional update/locking strategy, combined with service logic. Two separate read-then-write checks alone can race.

## 11. Security, identity, and browser boundaries

Spring Security's servlet integration uses a filter chain. Authentication determines identity; authorization determines allowed operations. Protect both endpoint access and object-level ownership. A valid token does not entitle its holder to every record ID. [Security architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html).

JWT is a token format, not encryption by default. Validate signature, issuer, audience, expiration, and relevant claims with a suitable library. OAuth 2.0 concerns delegated authorization; OpenID Connect adds identity-oriented functionality. Do not build password hashing or token verification from scratch for production.

CORS is a browser cross-origin policy and does not authenticate callers. CSRF matters particularly when browsers automatically attach credentials such as cookies. Choose protections from the actual credential transport and threat model instead of copying an unconditional disable-CSRF snippet. Output encoding, parameterized SQL, secret handling, and resource limits remain necessary.

## 12. Testing and operating Spring services

Unit-test domain rules without starting Spring. Use appropriate slices for controller or persistence tests and broader integration tests when wiring and infrastructure matter. Mocking every dependency cannot establish database transaction behavior. Real database integration tests may use disposable containers or an equivalent isolated environment.

Configuration should be explicit across profiles. Health checks indicate selected readiness/liveness conditions, not perfect business correctness. Structured logs, metrics, and traces answer different questions: events, aggregates, and request paths. Carry correlation IDs across calls and control sensitive fields.

For resilience, set timeouts, cap connections, retry only suitable failures, and use circuit breakers or bulkheads where appropriate. A circuit breaker temporarily stops calls to a failing dependency; it is not a retry loop. Graceful shutdown should stop accepting new work and handle in-flight tasks within a budget.

## 13. Build, versions, and capstone

The accompanying Spring project pins its parent version and Java target; the validation report states whether it compiled and tested. Do not infer compatibility solely from the machine's newest JDK. The documentation checked for this edition lists Spring Boot 4.1.1 and its supported Java range; deployed projects should use their own supported, tested dependency set. [System requirements](https://docs.spring.io/spring-boot/system-requirements.html).

Capstone: a book-reservation API with users, books, and reservations. Implement DTO validation, a transactional service, persistent uniqueness/availability protection, object-level permissions, pagination, structured errors, idempotent create handling, and tests for concurrent attempts. Add an AI suggestion service behind an interface while keeping reservation authority in the Java application service.

## 14. Oral exam with answers

**Why constructor injection?** Required dependencies are explicit and can be supplied in tests; it discourages hidden mutable setup.

**Why not return entities?** It couples clients to storage, can trigger accidental lazy loads, and can disclose unwanted fields.

**Can volatile replace a lock?** Only for suitable visibility/ordering use cases, not arbitrary compound invariants.

**Why equals and hashCode together?** Hash collections rely on equal keys producing compatible hash behavior.

**What is a proxy?** An object standing in for another to add behavior such as transactions or authorization around calls.

**Why might a transaction annotation not apply?** Calls can bypass the configured proxy, or configuration and transaction-manager scope may differ from assumptions.

**Does garbage collection close database connections promptly?** No. Use structured resource management and appropriate pools.

**When prefer a modular monolith?** When one deployment meets needs and strong internal boundaries give adequate maintainability without distributed coordination overhead.

**Coverage:** Detailed tutorials and labs cover Java basics, object design, collections, streams, exceptions, concurrency, dependency injection, layers, HTTP, transactions, security, and testing. JVM GC tuning, bytecode engineering, every Spring portfolio module, and every database-specific isolation behavior are advanced introductions or outside this notebook. The algorithms/patterns companion extends interview breadth without pretending a finite set covers all possible exams.


Advanced continuation: [10-java-spring-depth](10-java-spring-depth.html). The advanced workshop and accompanying projects extend the introductory scope described above.
