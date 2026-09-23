# Real-time and cache lab

Run from this folder with Python 3.11+ and the library's tested environment. Dependencies: FastAPI, uvicorn, httpx, pydantic and websockets. In a fresh virtual environment install the local pins with `python -m pip install -r labs/realtime-cache/requirements.txt` from the library root. Browser tests additionally need the Study Coach frontend dependencies and installed Playwright browser engines. The pins record the tested environment; they are not a full transitive lockfile.

For the automated isolated test, from the library root:

```powershell
.venv/Scripts/python.exe labs/realtime-cache/test_project.py
```

The test generates a temporary password and database in excluded `.runtime`, starts a loopback service on 8105, opens real HTTP/SSE/WebSocket connections and stops its owned service. Read `report.json` for assertions and limits. Do not run concurrently with another instance on that port.

To explore the browser UI, set a private `EVENT_PASSWORD` environment variable and `EVENT_DB` to an isolated writable database path, then run from this folder:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8105 --ws-max-size 4096
```

Open http://127.0.0.1:8105, select alice or bob and use your configured password. Same-origin cookies and explicit Origin checks are part of the design. If you change the origin/port, configure `EVENT_ORIGIN` consistently. This teaching login is not OIDC or a production password database. The server requires `EVENT_PASSWORD` at startup; do not publish the service publicly.

SQLite persists messages and idempotency records. In-memory sessions vanish on restart. Cache capacity is sixteen entries, TTL ten seconds; each snapshot rechecks the database revision. SSE retains fifty events per owner and rejects an expired cursor. WebSockets have a bounded lifetime and send deadline. The HTML page uses textContent for message rendering.

The report's short concurrent-write test is not an endurance benchmark. A separate `test_browser.py` run passed six journeys across Chromium, Firefox and WebKit at desktop and narrow widths, including keyboard login/logout, SSE/WebSocket delivery and axe checks; see browser-report.json. It uses the Study Coach frontend's installed Playwright/axe dependencies. Distributed Redis caching, clustered sessions, physical mobile devices and a cloud deployment are not established by these tests.

`python labs/realtime-cache/test_recovery_load.py` (from the library root) kills the server during concurrent writes, restarts it, reauthenticates clients and retries the same logical keys. The recorded run preserved all eighty acknowledged writes with no duplicate durable events. This is a bounded outage experiment, not a long endurance test; see recovery-report.json.
