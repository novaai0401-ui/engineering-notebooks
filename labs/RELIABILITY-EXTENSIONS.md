# Executed reliability extensions

Run commands from the engineering-notebooks folder. These tests are Windows-oriented process tests and use loopback ports. Reading the books requires none of these dependencies. For code, create a Python 3.11+ virtual environment and install the relevant requirements first; Java projects also need Java 21+ and Maven. Reports describe exactly what ran, including failures.

```powershell
py -3 -m venv .venv
.venv/Scripts/python.exe -m pip install -r labs/verification-requirements.txt
```

## Reliable logout: the registered-letter analogy

If a school closes a classroom, telling one teacher is insufficient. Write a delivery record for every teacher, keep trying absent teachers, and cross a teacher off only after acknowledgement. Our relay follows that idea. It checks the signed logout message, encrypts it in a SQLite journal and commits before returning HTTP 202. Each receiver has its own pending/delivered state. Duplicate message IDs are checked against the original content. Restart resumes pending deliveries.

```powershell
.venv/Scripts/python.exe labs/study-coach/test_durable_relay.py
```

The test forges a signature, uses a wrong audience, submits a duplicate, makes a receiver unavailable, kills the relay and restarts it. Both test sessions ultimately become revoked. The receivers validate real RSA signatures but are fixtures, not additional Spring instances. The five-minute delivery-validity boundary is deliberate: an expired delivery becomes a recorded failure. A production instance must reconcile revocations before becoming ready after a longer outage; a queue alone does not establish that guarantee. Production also needs shared or replicated storage, TLS, key rotation and retention.

For the actual Keycloak/Spring login diagnosis, first follow [Study Coach setup](study-coach/ADVANCED-RUN.md), including Java build, frontend browser dependencies and setup_identity.py. Run test_identity_cluster.py to create the isolated rotated-secret realm fixture, then `python labs/study-coach/test_identity_repeat.py`. The latter deliberately requires that private retained fixture; it is not a fresh-install setup command. It uses the newly built Java JAR, tests ten fresh logins and forty concurrent anonymous API probes, and stops its owned services. The private realm, credentials and runtime logs are excluded from the ZIP; recreate them locally rather than trying to copy secrets from the delivered package.

## Kafka: three copies of the class register

Three brokers store copies. With replication factor three and minimum in-sync replicas two, acknowledgements from the current in-sync set permit one broker failure while maintaining the configured replication requirement. Kill the actual partition leader, write ten more records, then restart the old leader and wait until all three replicas are in sync. A successful write is checked by reading the exact expected sequence.

```powershell
mvn -q -f labs/kafka-lab/pom.xml package -DskipTests
.venv/Scripts/python.exe labs/kafka-lab/test_cluster.py
```

This uses three real Kafka processes, not mocks. They share one computer: a machine failure would stop all three. Plaintext loopback is a classroom configuration. Independent-host failures, partitions, authentication and disk loss require additional tests.

## Endurance: a longer walk, not a marathon certificate

```powershell
.venv/Scripts/python.exe -m pip install -r labs/realtime-cache/requirements.txt
.venv/Scripts/python.exe labs/realtime-cache/test_endurance.py
```

One client repeatedly writes, retries the same key and reads the snapshot for five minutes. The test checks duplicate sequence IDs and durable request counts, while sampling memory and Windows handle counts. Read endurance-report.json for actual duration, throughput and latency. A stable five-minute graph cannot prove the absence of a leak that appears after a day. This test does not exercise Redis.

For a longer bounded run, use `python labs/realtime-cache/test_endurance.py --seconds 600`. Durations from 30 to 1,800 seconds are accepted. Non-default runs write a separate endurance-600-report.json (or the selected duration), preserving the original five-minute evidence. Compare memory, handles, duration and latency together; workloads sharing a busy machine are not controlled capacity benchmarks.

## Telemetry: receiving a letter versus filing it safely

```powershell
.venv/Scripts/python.exe -m pip install -r labs/collector-lab/requirements.txt
.venv/Scripts/python.exe labs/collector-lab/run.py
.venv/Scripts/python.exe labs/collector-lab/test_durable.py
```

The first command obtains the pinned collector with a digest check. The second test sends five actual spans while the destination is down. The collector retries when the destination returns. The teaching sink commits trace IDs to SQLite before acknowledging and retains them after a hard process restart. The collector queue in this test is memory-only: crashing the collector before delivery can lose spans. Sink durability and queue durability are separate properties. The sink is not a production trace-query platform.

The stronger variant is `python labs/collector-lab/test_durable.py --persistent`. It obtains the pinned contrib distribution with its own digest check, uses a file_storage queue, kills the collector while the destination is unavailable and restarts it before recovery. Read persistent-report.json for execution evidence. Its first download is approximately 103 MB; runtime binaries are excluded from the reading ZIP.

## AI evaluation: finding the right page versus answering correctly

```powershell
.venv/Scripts/python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
.venv/Scripts/python.exe labs/rag-flow/test_pretrained.py
.venv/Scripts/python.exe labs/rag-flow/test_integrated.py
.venv/Scripts/python.exe labs/rag-flow/test_factual_holdout.py
```

The setup command downloads model weights if absent. The retrieval test itself uses cached weights only. It uses the actual pretrained encoder, twelve fresh paraphrase questions and four attempts to cross an ownership boundary. Permissions are applied before encoding/ranking. Retrieving three neighbours for a nonsense question still returns three documents: similarity is not proof that an answer exists.

The factual test requires Ollama on localhost:11434 with qwen2.5:7b-instruct-q4_K_M already available. It sends eight fixed question/evidence pairs directly to generation: numbers, ownership, two-hop reasoning, absent evidence, a false premise, instruction injection and contradictory sources. Its expected short answers are declared before execution. Exact comparison is appropriate for these tightly specified answers; it is not a universal prose grader. Results are persisted after every case, including timeouts and wrong answers. These are fresh tutor-authored fixtures, not external independent adjudication.

The configurable RAG flow now accepts `embedding: "pretrained"` and, in agentic mode, `controller: "ollama"`. Use `python labs/rag-flow/rag_flow.py --config labs/rag-flow/pretrained-flow.json` or select model-agent-flow.json. The model chooses only search or finish; the application validates exact fields, query length and permitted retrievers. Search still uses the authenticated scope passed into the lab, and a hard step budget limits decisions. No model-produced shell code, URL or write action is executed. Final generation remains extractive unless separately configured. `python labs/rag-flow/test_integrated.py --model` runs an actual model-selected search with a one-step budget. This small test is not autonomous-agent reliability certification. The CLI user argument remains a fixture; production must obtain identity from authentication.

Model answer quality and operational timeouts remain visible even when integration works. `python labs/rag-flow/retest_abstention.py` is explicitly a development retest of one observed failure with a revised prompt; it must not be relabelled an independent holdout score.

## Remaining work that needs a real environment or learner

Public-cloud checks need a chosen account/project, region and cost limit. Device checks need an actual phone and screen reader. Personal grading needs unaided answers. Local Docker, Kubernetes and Redis runners are now supplied; their actual results are in the completion audit. These external acceptance requirements are not marked successful without evidence.

## Real application logout after an unavailable receiver

After preparing the isolated identity fixture described above, run `python labs/study-coach/test_durable_spring.py`. This starts actual Keycloak and two Spring instances. A proxy deliberately returns 503 for one logout receiver while its application remains alive. Keycloak signs the events; the relay records them, survives restart and retries after connectivity returns. One browser session initially remains valid, then becomes unauthorized when its delivery arrives. Both instances ultimately reject their revoked sessions. Four delivery records cover two session IDs and two recipients. This is network unavailability, not a claim that in-memory sessions survive application process death. The initial failed harness attempt remains in durable-spring-initial-report.json.

## Shared real-time storage across processes

Run `python labs/realtime-cache/test_multi_instance.py`. Two processes share a SQLite WAL database, with independent authenticated connections. A write on A reaches an already-connected WebSocket and SSE reader on B. Their ETags change with the durable revision. BEGIN IMMEDIATE takes the writer reservation before allocating a sequence or checking an idempotency key: two separate Python locks alone cannot protect a shared database. The test races identical keys and eighty distinct writes. This design uses database polling on one host; it does not demonstrate independent-host Redis Pub/Sub.

## Model-extracted graph and measured generation limits

With the documented Ollama model available and NetworkX installed, run:

```shell
python labs/rag-flow/test_graph_pipeline.py
python labs/rag-flow/test_bounded_generation.py
python labs/rag-flow/test_development_regression.py
```

The first test obtains actual model-extracted relationships, verifies quotes, persists them and checks permission-filtered traversal, communities, source updates and deletion. Think of each edge as a labelled string between two cards, with its source page attached. Remove or hide a page and its derived strings must disappear from that reader's view too. Quote presence checks provenance; they cannot establish that every extracted relation is true. Community summaries here are extractive, and entity matching is normalized exact-name matching.

The bounded-generation test passed the previously timed-out injection example with 1,024 context tokens, a 24-token generation budget and a constrained answer schema. The next test intentionally reuses known cases and is labelled development regression. It passed six of eight: the entity question returned UNKNOWN, and absent-evidence reasoning timed out. Do not replace these failures with a passing retrieval score or call reused questions an independent benchmark. The earlier strict baseline remains unchanged. The application still defaults to extractive output; model answer quality is an open limitation.

## Redis, containers and Kubernetes

Follow the ordered commands in [Laptop and mobile setup](../STUDY-ON-ANY-DEVICE.md). The Redis test uses three actual servers and three Sentinels: kill the leader, discover its replacement, check retained/new data and TTL, then verify the returning old leader becomes a replica. All run in one VM. Asynchronous replication is not a zero-loss guarantee.

The Docker runner builds the supplied React/Java and Python images and exercises an authenticated, approved, idempotent job with an SSE response, followed by web-container restart. The Kubernetes runner first tests controller replacement and scaling, then imports those built images, creates a temporary namespace, Secret, Services and persistent volume, and checks the same job after pod replacement. Read the JSON reports for outcomes; a runnable test is not evidence that it passed on your machine. No cloud resources are created.
