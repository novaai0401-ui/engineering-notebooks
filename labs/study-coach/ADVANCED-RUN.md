# Run the expanded projects

Read notebooks 16–21 first. These scripts run actual services and use random classroom credentials. They bind only to loopback and refuse occupied ports. They create private runtime state under the notebook library's `.runtime` folder. That folder is excluded from the distributed ZIP.

Prerequisites: Python 3.11 with the top-level pinned requirements, Node with `npm ci` in `frontend`, Java 21 or newer, Maven, and (for the distributed test) PostgreSQL binaries. The recorded Windows run used PostgreSQL 18.1. Set `PG_BIN` if installed elsewhere. The driver can use the installed PostgreSQL `libpq` through psycopg's Python implementation.

Build frontend with `npm run build`, then Java with `mvn package`. Do not rebuild an artifact while a running Windows process holds that same JAR open; the distributed harness copies its JAR into the private runtime directory.

From the library root, using its Python environment:

```powershell
.venv/Scripts/python.exe labs/study-coach/test_system.py
.venv/Scripts/python.exe labs/study-coach/test_distributed.py
.venv/Scripts/python.exe labs/study-coach/setup_identity.py
.venv/Scripts/python.exe labs/study-coach/test_identity.py
.venv/Scripts/python.exe labs/study-coach/test_identity_cluster.py
.venv/Scripts/python.exe labs/study-coach/python/test_live_model.py
.venv/Scripts/python.exe labs/study-coach/test_live_stack.py
.venv/Scripts/python.exe labs/study-coach/setup_monitoring.py
.venv/Scripts/python.exe labs/study-coach/test_monitoring.py
```

Run the service suites sequentially on a small machine. Identity startup includes database migration and can take several minutes. The scripts are integration exercises, not installers for public production infrastructure.

The live-model tests require a running local Ollama service with `qwen2.5:7b-instruct-q4_K_M` already available. They perform actual inference and can take several minutes. The test never stops an Ollama service it did not start. Model weights are not bundled.

Read `live-stack-review.json` alongside the mechanical integration report: the recorded generated answer used a valid citation but made an incorrect claim about checkpoint idempotency. The factual review failed. The extractive default remains the appropriate mode for this small teaching corpus when no factual review is available; the optional model output is an experimental draft. The integration test measures wiring, completion and citation identifiers, not semantic correctness.

The full-stack model test sets a 200-second lease and a 185-second worker deadline to accommodate local inference before the first token. This is intentionally different from the short extractive default. Independent lease heartbeats are a useful further production extension; increasing a lease also increases recovery delay after a crash.

`identity/realm-template.json` contains placeholders, not usable secrets. The harness imports generated values into a private dev database. Its administration helper changes only the newly created classroom realm. Public identity deployment needs TLS, managed persistent storage, appropriate hostname/cookie configuration, backup and lifecycle monitoring. The added cluster harness tests two reachable instances through a synchronous signed-logout relay and restarts both with a rotated secret. Its final isolated run passed; earlier login failures remain an unresolved intermittent finding. Read identity-cluster-failure-review.json. The relay is not durable and does not implement shared sessions or unavailable-instance recovery. Diagnostic settings/logs stay in excluded .runtime and must remain private.

The subsequent repeat-login investigation reproduced one failure in ten attempts while the rotated secret was accepted. The OIDC chain now disables unnecessary saved-request caching and logs only callback error codes. The latest test_identity_repeat.py report passed ten logins and forty anonymous API probes without session creation; this supports the competing-session mitigation without conclusively proving every historical cause. A separate identity/durable_relay.py implementation and test_durable_relay.py verify encrypted journal recovery and signed delivery to an unavailable receiver fixture. That fixture test is not a full replacement for the original Spring-cluster relay. See [Reliability extensions](../RELIABILITY-EXTENSIONS.md) for commands and boundaries.

Native Prometheus scraping and an alert fixture are exercised by the monitoring harness, which also writes a saved dashboard. The separate `labs/collector-lab/run.py` now downloads/verifies and runs a native OTLP collector, checks a real exported span and stops it. Docker/Kubernetes and cloud deployment remain unexecuted. Consult the generated validation report for exact passing checks and remaining limitations rather than treating the existence of a file as proof of deployment.
