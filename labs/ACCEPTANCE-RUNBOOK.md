# From a recipe to evidence

Imagine a fire drill. Writing the exit route is useful. Walking it reveals a locked door. Neither proves that everyone can evacuate during a real fire. Our lessons, local experiments and production acceptance have the same relationship.

Run commands from the **engineering-notebooks** folder. Read the JSON report after each command; a command printed in a book is not a passing result. Each report preserves what the experiment can establish.

## 1. Can the database really use this index?

On the prepared Windows lab, start the owned Docker daemon, then run each database separately:

```powershell
.venv/Scripts/python.exe labs/start_docker_lab.py
.venv/Scripts/python.exe labs/run_linux_lab.py mysql
.venv/Scripts/python.exe labs/run_linux_lab.py oracle
```

On Linux with Docker already available, use `python3 labs/database-plan-workshop/test_engines.py mysql` or replace `mysql` with `oracle`. Initial downloads can be large. If Docker Hub is unavailable, the Oracle runner accepts `--image ghcr.io/gvenzl/oracle-free:23-slim` on Linux; this maintainer registry was used for the passing run. No database ports are published. The runner creates a disposable container and removes only that container and its anonymous volumes afterward. Never adapt its cleanup to a production database.

The MySQL experiment compares a table scan with a covering index lookup, then deliberately removes an equality predicate. It also restores a logical backup into a second database and compares all 1,000 rows and their fields. The Oracle experiment captures estimated and executed plans with actual row counts. Oracle Free execution does not certify Oracle 19c compatibility. Read the engine version and image digest in each report.

**Explain it back:** Why can a correct index still lose to a table scan? Answer: a tiny table, low selectivity or inaccurate estimates can make another plan cheaper. An index name alone is not a performance result. Compare actual work under realistic data and parameters.

## 2. Does the secure socket really work through the proxy?

```powershell
.venv/Scripts/python.exe labs/run_linux_lab.py tls-websocket
```

This requires NGINX, OpenSSL and aiohttp in the Linux environment. The test creates a temporary certificate trusted only by its client. A normal untrusted client must reject it. Missing authentication and hostile Origin values must fail before WebSocket upgrade. A valid connection exchanges frames before and after NGINX reload.

**Explain it back:** Why is a local trusted test certificate not public HTTPS acceptance? Public deployment adds DNS ownership, a public certificate chain, renewal, provider routing and the real client network. None follows from disabling certificate verification; this test never disables it.

## 3. Does logout survive a process crash?

Use the identity setup in [Reliability extensions](RELIABILITY-EXTENSIONS.md) first. Run identity tests sequentially because they share the classroom ports.

```powershell
.venv/Scripts/python.exe labs/study-coach/test_durable_spring.py --crash
.venv/Scripts/python.exe labs/study-coach/test_durable_spring.py --crash --expire
.venv/Scripts/python.exe labs/study-coach/test_secret_overlap.py
```

The crash variant retains a live session behind an unavailable logout receiver, kills the actual Spring process, restarts it and tests the original browser cookie before delivery recovers. The current profile keeps sessions in memory: the restart loses them, so the old cookie must be rejected. This is useful fail-closed behavior, not durable shared-session recovery.

The expiry variant deliberately moves the journal delivery deadline into the past. It checks that undeliverable events become expired instead of replaying an expired token. Old cookies still fail after restart. A shared persistent session store would require a durable revocation ledger and reconciliation before readiness; this variant does not implement that store.

The overlap test uses a new disposable Keycloak realm. Twenty token requests alternate between old and new client secrets during the overlap window. After explicit retirement, the old secret must fail and the new one must work. Token introspection is recorded before and after rotation as a separate observation. Do not assume that successful client-secret retirement establishes every access-token and session-revocation behavior. The initial run retained a failed token-status assertion; the overlap checks themselves succeeded. This test is not a rolling Spring deployment. The policy follows the [Keycloak administration guide](https://www.keycloak.org/docs/latest/server_admin/).

## 4. Is the model right, or merely confident?

```powershell
.venv/Scripts/python.exe labs/rag-flow/test_expanded_evaluation.py
.venv/Scripts/python.exe labs/rag-flow/test_public_evaluation.py
```

Use the documented Ollama model. The first runner freezes 16 new tutor-authored factual/adversarial examples. The second uses 12 deterministic, externally labelled SQuAD 2.0 development examples, six answerable and six unanswerable, with short contexts and answers. Its manifest fixes selection before model execution. These filters make it a small diagnostic subset, not a representative benchmark or official SQuAD score. Public training contamination is possible.

Exit code 1 means at least one answer failed. Keep that report. Do not delete the question, silently change the expected answer or combine unlike datasets into a single advertised accuracy number. Generation with supplied evidence is a different test from permission-filtered retrieval.

SQuAD 2.0 is by Pranav Rajpurkar, Robin Jia and Percy Liang. Dataset and derived report excerpts are under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); see the [dataset site](https://rajpurkar.github.io/SQuAD-explorer/). The raw downloaded dataset stays in the excluded `.runtime` folder.

## 5. Can a reader reach the overflowing example?

```shell
node check_accessibility.mjs
node check_reading.mjs
```

These use the installed Playwright and axe dependencies in the capstone frontend. They check all 38 reading pages at two widths. Scrollable code regions now accept keyboard focus and show a focus outline. Browser automation can find inaccessible regions; it cannot tell us exactly what VoiceOver announces on a physical iPhone. Complete the separate [manual worksheet](MANUAL-ACCEPTANCE.md).

## 6. Does the service remain correct for longer?

```powershell
.venv/Scripts/python.exe labs/realtime-cache/test_endurance.py --seconds 1800
```

The 30-minute workload writes, retries with the same idempotency key, reads snapshots and samples resources. It reconciles durable request counts. This is a bounded single-client run on a shared computer, not a multi-day leak study or production capacity test. Inspect the full resource series rather than one favorable sample.

## 7. What genuinely needs another environment?

Cloud account/project, region and budget select the actual deployment target. Public TLS and provider disaster recovery need that target. Independent-host failure tests need independent hosts. A physical screen reader needs the device and a person recording observations. Interview grading needs the learner's original answers. These are acceptance inputs, not gaps that can be closed by generating more prose.

After the Linux tests finish, stop only the classroom distribution with `wsl --terminate EngineeringNotebookLab-13e66a98`. Do not stop a model server or unrelated service that the learner owns.
