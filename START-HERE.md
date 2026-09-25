# Your personal engineering classroom

Start with the story, say the idea in your own words, trace the small example on paper, then change the code. You do not need another website to read these lessons. External links credit the official sources and are optional reading. Running examples does require the documented software.

## Choose a notebook

The expanded library contains 30 notebooks. For exact folders and commands, start with [Study on any device](STUDY-ON-ANY-DEVICE.html). The [completion audit](COMPLETION-AUDIT.html) separates executed checks from remaining verification. After the foundation and advanced workshops, continue with:

| New notebook | What it adds |
| --- | --- |
| [16. Real model engineering](16-live-model-engineering.html) | Actual local generation, tool selection, budgets, citation gates and evaluation limits |
| [17. Identity and deployment](17-identity-and-deployment.html) | OIDC/PKCE, roles, sessions, revocation, secret rotation and release decisions |
| [18. Distributed systems lab](18-distributed-systems-lab.html) | PostgreSQL, persistent broker, two workers, outbox/inbox, isolation and restore |
| [19. Observability and browsers](19-observability-and-browser-quality.html) | Traces, metrics, alerts, measured load, three browser engines and accessibility |
| [20. Specialist algorithms and math](20-specialist-algorithms-and-math.html) | Fenwick/segment trees, KMP, SCC, flow, gradients, attention and least squares |
| [21. Assessed interview route](21-assessed-interview-route.html) | Diagnostics, timed rounds, explicit answer keys and grading rubrics |
| [22. Kafka](22-kafka-event-engineering.html) | Partitions, groups, transactions, offsets, duplicates and a real broker restart lab |
| [23. Docker](23-docker-and-release-engineering.html) | Images, containers, builds, networking, release and recovery |
| [24. Kubernetes](24-kubernetes-from-pods-to-recovery.html) | Controllers, Pods, probes, scaling, security, storage and deployment recipes |
| [25. Cache management](25-cache-management-and-consistency.html) | TTL, LRU, stampedes, version fences, Redis principles and ETags |
| [26. Real-time delivery](26-websockets-sse-and-realtime-delivery.html) | SSE, WebSockets, replay, revocation, backpressure and scaling |
| [27. Reliability](27-reliability-evaluation-and-operations.html) | Failure tests, deadlines, telemetry, identity and factual evaluation |
| [28. Full-stack capstone](28-fullstack-capstone-and-assessment.html) | Request flow, contracts, acceptance tests and scored interview rounds |
| [29. Databases](29-databases-for-fullstack-and-ai.html) | SQL, modelling, transactions, indexes, JPA/Python, NoSQL, Redis and vectors |
| [30. RAG flows](30-rag-patterns-and-user-defined-flows.html) | Simple, Hybrid, Graph, Multi-Hop, Agentic and Adaptive RAG with configurable examples |

The latest execution evidence and remaining environment-dependent checks are in [Validation](VALIDATION.html). Reading is fully offline. Executing distributed labs needs installed services and dependencies; no live-model weights or runtime credentials are bundled.

The [saved monitoring dashboard](labs/study-coach/monitoring-dashboard.html) shows a measured local scrape. [Advanced run instructions](labs/study-coach/ADVANCED-RUN.md) explain how to repeat the model, identity, distributed-system and monitoring integrations. The supplied `.github/workflows/study-coach.yml` is an unexecuted CI/container recipe for using this library directory as a repository root.

Notebook 16 includes an actual failed factual review: the experimental model confused checkpointing with idempotency despite using a valid citation. The lesson supplies the correction. Keep the default extractive mode when you cannot review generated claims.

| Notebook | What you learn | Working practice |
| --- | --- | --- |
| [Agents](01-agent-engineering.html) | Agent types, harnesses, LangChain, LangGraph, Deep Agents, MCP, FastMCP, parallel work, orchestration, safety and evaluation | 11 executable labs including actual framework calls with a scripted model |
| [Python for AI](02-python-for-ai.html) | Python foundations, arrays, tables, ML pipelines, gradients, retrieval, concurrency and design | 12 executable labs |
| [Java and Spring Boot](03-java-spring-boot.html) | Objects, collections, concurrency, SOLID, dependency injection, HTTP, transactions, security and testing | 4 Java labs plus a tested Spring project |
| [React](04-react-and-frontend.html) | Browser foundations, JavaScript, state, reducers, effects, hooks, accessibility and testing | 2 JavaScript labs plus a tested interactive React project |
| [Full-stack AI architecture](05-fullstack-ai-architecture.html) | React + Java + Python boundaries, SQL, identity, retrieval, queues, reliability and deployment | 3 executable labs and an integration capstone specification |
| [Algorithms and patterns](06-algorithms-and-design-patterns.html) | Core problem-solving techniques, data structures, design principles and all 23 classic GoF patterns | 13 executable labs plus pattern selection exercises |

Every notebook has a readable HTML edition, editable Markdown, and a Jupyter notebook. Executable cells retain recorded outputs; architecture and interview workbooks primarily contain guided reading and exercises. Java and JavaScript notebooks use a Python kernel that launches the installed Java or Node runtime. Code labelled as a recipe is displayed for study rather than automatically executed.

## Continue into the nine advanced workshops

| Notebook | Depth added |
| --- | --- |
| [7. Durable agents](07-durable-agents.html) | Persistent approvals, migration, leases, fencing, cancellation, memory and evaluation |
| [8. Remote MCP](08-remote-mcp.html) | Actual HTTP server/client, credentials, scopes, ownership, deadlines and deployment |
| [9. Python AI depth](09-python-ai-depth.html) | Packaging, typing, profiling, statistics, numerical stability and ML from scratch |
| [10. Java/Spring depth](10-java-spring-depth.html) | JVM, generics, concurrency, isolation, JPA query counts, optimistic locking, outbox and cache |
| [11. React depth](11-react-depth.html) | Closures, event loop, TypeScript, server state, routing, hydration and browser tests |
| [12. Algorithms depth](12-algorithms-depth.html) | Trees, graph ordering, union-find, tries, backtracking, DP and correctness arguments |
| [13. Pattern workshop](13-patterns-workshop.html) | All 23 GoF patterns implemented with assertions, alternatives and failure modes |
| [14. Connected full-stack workshop](14-fullstack-workshop.html) | The implemented React + Java + Python Study Coach and its failure tests |
| [15. Interview practice](15-interview-practice.html) | Timed rounds, graded exercises, detailed answers and follow-up questions |

Pair each foundation notebook with its advanced continuation. Work through notebook 14 while reading the corresponding source files under `labs/study-coach`. Its [run guide](labs/study-coach/README.md) explains exact commands. The remote protocol project is in `labs/remote-mcp`, and the installable Python package is in `labs/python-package`.

## A learning route that builds understanding

If you are new to programming, begin with Python lessons 1–7, then Java foundations and browser/JavaScript foundations. Learn the agent notebook after functions, classes, exceptions and async make sense. Study algorithms throughout rather than saving them for the end.

| Weeks | Focus | Evidence that you understand |
| --- | --- | --- |
| 1–3 | Python foundations and basic problem solving | Predict output before running it; explain mutation and loops |
| 4–6 | Python AI data flow, core algorithms | Build a leakage-safe pipeline; trace BFS and binary search |
| 7–9 | Agents, graphs, MCP and orchestration | Trace a tool call, stop a loop, explain retries and permissions |
| 10–12 | Java, Spring and transactions | Run the service tests; explain constructor injection and rollback |
| 13–15 | JavaScript, React and browser behavior | Change the study app and test it with keyboard interactions |
| 16–18 | Full-stack boundaries and reliability | Draw a request path, failure path and authorization boundary |
| 19–21 | Patterns and interview drills | Choose a pattern, explain its cost and reject an unnecessary one |
| 22–24 | Capstone and mock interviews | Implement an integrated slice and defend its design decisions |

This is a flexible route, not a promise that everyone learns at the same speed. A useful daily session is 20 minutes reading, 20 tracing, 30 coding, and 10 explaining without notes.

## How to answer an interview question

Use five steps: define the idea simply; give a tiny example; explain the mechanism; discuss a failure case or tradeoff; describe how you would test it. For algorithms, state input assumptions, a straightforward solution, the improved solution, complexity and edge cases. For architecture, begin with requirements and constraints before naming technologies.

For each exercise ask: What happens with empty input? What if two requests arrive together? What if a dependency fails? Who is allowed to do this? How do I know the answer is correct? Where does the data go?

## Read offline

Open `index.html` in a browser. All lesson styling is embedded; there are no CDN dependencies. You can print an HTML lesson to PDF using the browser. Keep the folder together so local links work. The original AI Interview Book is a separate companion and is not overwritten by this collection.

## Run the notebook labs

Use Python 3.11 with the tested versions in `requirements-tested.txt`. From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-tested.txt
.\.venv\Scripts\python run_notebook_labs.py --book 01-agent-engineering
```

Omit `--book` to run all notebooks' executable cells. Java labs also require a JDK supporting `javac --release 21`; JavaScript labs require Node.js. Installations may download large scientific packages, especially PyTorch. Package pins identify what was tested on this Windows machine; availability on another platform can differ.

To use a notebook editor, install Jupyter or an editor with notebook support and select this Python environment. Run cells from top to bottom. Some cells depend on earlier definitions. Files under `labs/python` are source fragments ending in `.cell.txt`, not standalone programs; the runner handles their ordering and top-level async code.

The framework labs use a deterministic scripted model. They exercise real framework behavior without API keys, paid calls or external model services. A scripted model is not a trained language model, and its passing tests do not demonstrate model reasoning quality. Provider-backed recipes require separate configuration and have not been provider-tested here.

## Run the Spring Boot project

From `labs/spring-demo`, with Java and Maven installed:

```powershell
mvn test
mvn spring-boot:run
```

Open `http://127.0.0.1:8089/api/greeting?name=Asha` while the application runs. Stop it with Ctrl+C. This small local teaching service demonstrates injection, validation, HTTP mapping and tests. It is not an authenticated production service.

## Run the React project

From `labs/react-demo`, with Node.js and npm installed:

```powershell
npm ci
npm test
npm run build
```

Open `dist/index.html`. Add a topic, mark it complete and observe the count. The app stores its state in memory: refreshing clears it. The packaged build can be opened without installing Node; Node is needed to edit, rebuild and run its tests.

## Coverage and honest limits

For the supplied Java/Spring interview questions, read [Notebook 31: interview masterclass](31-java-microservices-interview-masterclass.html). It connects every question to an answer, example and follow-up, including microservice patterns, all 23 GoF pattern families, SOLID, MySQL/Oracle plan diagnostics and actual Spring Batch restart tests. From the library root, run `mvn -f labs/interview-workshop/pom.xml test` for the isolated Spring/JUnit/Mockito workshop, or `python run_notebook_labs.py --book 31-java-microservices-interview-masterclass` for the notebook's Java/Python cells. The SQL engine-specific examples are labelled recipes, not unrecorded database tests.

The original six books teach foundations; nine advanced workshops add working implementations and deeper practice. All 23 GoF patterns now have executable small implementations. The Study Coach is a complete local integration with authentication, durable jobs, streamed extractive answers and failure tests. It is a teaching application, not a production-certified service or a deployed generative model. Docker deployment recipes are provided; container execution and external model-provider calls are not claimed as tested unless recorded in the validation report.

No finite collection can include every algorithm, every design pattern or every future framework change, and no book can guarantee every exam result. Advanced compiler work, formal verification, specialist numerical methods, complete cloud operations, every Spring module and every research algorithm are outside this collection. Use the worked examples and exercises to develop the reasoning needed for unfamiliar questions. Check [the validation report](VALIDATION.html) for exactly what ran.
