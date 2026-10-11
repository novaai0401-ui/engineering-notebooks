# API Automation Kit + Spring Boot VS Code Kit: final setup

Assumes the main Copilot kit is installed (`C:\copilot-kit` with agents/prompts folders and the VS Code user settings
pointing at them). If not, do Part A of `copilot-agents-kit\FINAL-SETUP.md` first.

## Part 1: install both kits into Copilot (once, 5 min)

1. Extract `api-automation-kit.zip` to `C:\copilot-kit\api-automation-kit\`.
2. Extract `springboot-vscode-kit.zip` to `C:\copilot-kit\springboot-vscode-kit\`.
3. Copy the agents and prompts into the folders VS Code already watches:
   - `C:\copilot-kit\api-automation-kit\.github\agents\*`      -> `C:\copilot-kit\agents\`
   - `C:\copilot-kit\api-automation-kit\.github\prompts\*`     -> `C:\copilot-kit\prompts\`
   - `C:\copilot-kit\springboot-vscode-kit\.github\agents\*`   -> `C:\copilot-kit\agents\`
   - `C:\copilot-kit\springboot-vscode-kit\.github\prompts\*`  -> `C:\copilot-kit\prompts\`
4. VS Code: `Ctrl+Shift+P` -> `Developer: Reload Window`.
5. `Ctrl+Alt+I`, Agent mode, open the agent dropdown: confirm `api-inventory`, `api-journey`, `api-test-builder`,
   `api-runner`, `spring-vscode` are listed. Type `/` and confirm `/api-inventory`, `/api-journey`, `/api-tests`,
   `/api-run`, `/api-all`, `/spring-vscode`, `/spring-run`.

## Part 2: API Studio, your own Postman (once, 3 min)

1. Open a terminal:
   ```
   cd C:\copilot-kit\api-automation-kit\api-studio
   npm install
   npm start
   ```
2. Open http://localhost:4545.
3. Tab **1. Config**: base URL, default headers, auth (bearer token, or a login request + token JSONPath), variables,
   DB (optional). Use `env:NAME` for any secret, e.g. password `env:API_TEST_PASSWORD`. Click **Save config**.
4. Load secrets into the terminal before running (values come from the main kit vault):
   ```
   powershell -File C:\copilot-kit\secrets.ps1 env
   ```
   then restart `npm start` from that same terminal so the server sees them.
5. Sanity check: tab **4. Run**, journey `example-orders`, mode `mock`, Run. All three steps should PASS.

## Part 3: per repo, API automation (first time 15-30 min, then minutes)

1. Open the backend repo in VS Code (frontend repos work too for the APIs they call).
2. `/api-inventory` -> approve the grep/terminal commands. Check `api\INVENTORY.md`: exposed, consumed, config, dependency map.
3. `/api-journey` -> type `all` (or a name like `checkout`). Check `api\JOURNEYS.md` for coverage.
4. Point API Studio at the repo's journeys so the UI shows them:
   ```
   set JOURNEYS_DIR=C:\path\to\repo\api\journeys
   npm start
   ```
   (or copy the journey files into `api-studio\journeys\`).
5. In the UI, Config tab: fill the variables the inventory listed (`PAYMENT_API_URL`, tokens as `env:`), save.
6. Run a journey from the UI in `live` mode against your local or dev environment, or from the chat: `/api-run checkout`.
7. `/api-tests` -> generates `api\tests\` (code suite + curl scripts + run.ps1). Run one:
   ```
   .\api\tests\run.ps1 -Journey checkout
   ```
8. Keep `api\` out of git if you cannot commit: add `api/` to `.git\info\exclude`. Re-run `/api-inventory` after merges; it is always fresh.

Manual use without any agent: Import tab -> upload OpenAPI / journey JSON / XML -> Run tab. Copy curl per step from the results table.

## Part 4: per Spring Boot repo, VS Code instead of IntelliJ (first time 10-20 min)

1. Open the Spring Boot repo in VS Code. Make sure the JDK the project needs is installed (`java -version`); if not, the agent prints the winget command and waits.
2. `/spring-vscode` -> approve commands. The agent writes `.vscode\` (settings, launch, tasks, extensions, api.http), installs extensions, compiles, runs the local profile, hits `/actuator/health`, runs one unit test, and records all of it in `.github\copilot-context\SETUP.md`.
3. When it asks, run `Developer: Reload Window`. If Java import looks wrong: `Java: Clean Java Language Server Workspace`.
4. Secrets for local runs: copy `.env.local.example` to `.env.local` (git-excluded) or run `secrets.ps1 env` in the terminal before pressing F5; launch.json reads `${env:NAME}`.
5. Daily:
   - `F5` -> "Spring Boot: local" (debugger attached).
   - `Ctrl+Shift+B` -> build tasks; `Ctrl+Shift+P` -> `Tasks: Run Task` -> `maven: test one`.
   - Test explorer (beaker icon) runs JUnit tests with the test profile.
   - `.vscode\api.http` -> click "Send Request" for quick calls, no Postman.
   - `/spring-run local` -> build, run, health check, optional API journey, stop.
6. IntelliJ run configs are translated into launch configs; `.idea\` stays untouched, so teammates on IntelliJ are unaffected.

## Part 5: end-to-end flow for a backend ticket (what a normal day looks like)

1. `/spec` (main kit) for the requirement, or skip for a small ticket.
2. `/feature` or `/java-task` to implement; it reads CONTEXT.md and the Touch list.
3. `/spring-run local` to run the app.
4. `/api-inventory` if endpoints changed, `/api-journey <journey>` then `/api-run <journey>` to prove the flow end to end (DB checks included).
5. `/review`, then open the PR.

## Checks that it is working

- Agent dropdown shows the 5 new agents; `/` shows the 7 new prompts.
- `npm start` prints "API Studio on http://localhost:4545" and the mock run of `example-orders` passes.
- `node cli.js run <journey> --junit reports\junit.xml` exits 0 on a green journey, 1 on a failure (CI-ready).
- Spring Boot: F5 starts the app and `.vscode\api.http` health request returns 200.

## Guardrails
- Inventory, journeys, config and reports never contain secret values; `env:` refs and the vault only.
- The runner refuses base URLs containing "prod" unless `allowProd` is set; Authorization and DB passwords are masked in reports and curl.
- No agent modifies application source, pom/gradle files or `.idea`.
