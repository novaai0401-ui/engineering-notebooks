# Study Coach — a connected teaching application

React/TypeScript runs in the browser. Spring Boot authenticates two local learners, enforces CSRF and ownership, migrates an H2 database, persists jobs, runs a bounded-attempt worker, and streams snapshots over SSE. Python ranks authorized documents using TF-IDF and streams quoted evidence. No paid model, API key, or fabricated model response is used.

## Build

Install the notebook root's `requirements-tested.txt` into its Python environment. Use Java 21 or later, Maven and Node.js. From this directory:

```powershell
Set-Location frontend
npm ci
npm run build
npx playwright install chromium
Set-Location ../java
mvn -B -ntp package
Set-Location ..
```

The frontend build writes static assets into the Java project. Maven runs eight database/service integration tests before packaging.

## Run locally

Set `COACH_PASSWORD` to a password of at least 12 characters and `COACH_SERVICE_TOKEN` to a long random secret. These are local classroom credentials, not shared production credentials. Both sample users, `alice` and `bob`, use this classroom password so you can compare ownership behavior.

```powershell
$env:COACH_PASSWORD = 'choose-your-own-long-local-password'
$env:COACH_SERVICE_TOKEN = (& ../../.venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(32))")
../../.venv/Scripts/python run_local.py
```

Open http://127.0.0.1:8091 after startup. Create a question, approve it, and watch the answer. Try “Alice private plan” as each user. Refresh/reconnect recovers a selected job's current snapshot. Page refresh clears the selection; database records remain in `java/data`. Ctrl+C stops only the two processes launched by the script. The launcher refuses to take over occupied ports.

## Verify the entire system

From the notebook root run:

```powershell
.\.venv\Scripts\python labs/study-coach/test_system.py
```

This uses temporary credentials and a temporary database, starts actual services on ports 8091 and 8092, runs network checks and Chromium/Firefox/WebKit tests, kills and restarts Java to verify recovery, stops Python to verify bounded failure, and cleans up its own processes. Do not run it while the manual app is using those ports. Results are written to `system-report.json`, `frontend/test-results/report.json`, and log files. It never deletes a user's persistent classroom database.

## Container deployment recipe

With Docker and Compose installed and the same two environment variables set:

```powershell
docker compose up --build
```

The web port is bound to loopback; Python is reachable only on the Compose network. The H2 data volume persists across container recreation. Use `docker compose down` to stop; do not add volume deletion flags if you want to retain data. These container definitions are provided as a deployment recipe; consult the validation report for whether a container runtime was available and tested. Public deployment additionally needs TLS, real user/identity lifecycle, secret rotation, capacity limits, operational monitoring and backup restoration tests.

## Deliberate limits

The default profile uses extractive retrieval, H2, local classroom credentials and one polling worker. Optional modes add actual Ollama generation, OIDC login, PostgreSQL, persistent broker delivery, multiple workers, trace propagation and protected metrics. See [Advanced run instructions](ADVANCED-RUN.md) and the generated integration reports for what was executed. Events remain bounded-lived snapshots with manual reconnect. Small built-in evidence and local tests do not establish production capacity, complete model reliability or security certification.
