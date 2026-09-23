# Native Kafka lab

Requires Java 21+, Maven, Python and httpx in the course environment. It uses Kafka 4.1.2 intentionally pinned for this experiment, not a claim about the latest release.

From this folder run `mvn -q package`; then from the library root run `.venv/Scripts/python.exe labs/kafka-lab/run.py`. Maven resolves the broker/client dependencies into excluded target/dependency. The runner creates a private KRaft data directory under excluded .runtime, starts a broker on loopback 19092 with controller 19093 and stops only its own processes.

The Java exercise commits two ordered records and aborts one transaction. The runner kills/restarts the broker retaining its logs; a read_committed consumer sees only committed records. Offset commit/resume is checked and two group members acquire different partitions. Read report.json for the observed results.

This is a one-node plaintext test. It does not establish multi-node replication, SASL/TLS, schema registry integration or database/Kafka atomicity. Docker and Kubernetes packaging are separate unexecuted concerns. Do not expose these local ports publicly.
