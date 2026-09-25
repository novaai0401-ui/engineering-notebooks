# Interview workshop

Run from the library root: `mvn -f labs/interview-workshop/pom.xml test`.

Requires Java 21+, Maven and internet for uncached dependencies. This isolated example pins Spring Framework 6.2.12 / Spring Batch 5.2.4, JUnit 5.13.4, Mockito 5.20.0 and H2 2.3.232. It does not alter the existing Boot 4 capstone.

- PaymentServiceTest: constructor injection, correct amount, rejected input and persistence failure using Mockito.
- TransactionBoundaryTest: actual Spring proxy rollback versus same-class invocation with H2 autocommit.
- BatchRestartTest: actual two-item chunk commit, injected writer failure/rollback, checkpoint restart with identical identifying parameters, distinct executions of the same instance, and completed-instance rejection.

The intentional Batch failure is expected during the test. The JUnit result, not the presence of an error in that expected job log, determines test success. These are local H2 tests; they do not establish MySQL/Oracle execution plans, remote payment exactly-once behavior or process-kill recovery. The test report records actual execution.
