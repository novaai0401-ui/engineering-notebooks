# Study on a laptop, tablet or phone

## 1. Choose reading or running

All thirty HTML notebooks can be read without an internet connection, account or model. Each has matching Markdown and Jupyter editions. Recorded code outputs are included. Running the code requires the appropriate runtime; reading on a phone does not execute Java, Docker or model inference on that phone.

Unzip Engineering-Notebooks.zip. The folder containing index.html, study_server.py and START-HERE.html is the library root. You can move that folder to another Windows, macOS or Linux laptop. For basic laptop reading, open index.html in a browser; no command is required.

## 2. Your current Windows folder

Open PowerShell and run:

```powershell
cd 'C:\Users\chand\.codex\visualizations\2026\09\23\01a0cd61-437a-7413-b921-13e66a982345\engineering-notebooks'
py -3 study_server.py
```

If the Python launcher is unavailable but Python is on PATH, use `python study_server.py`. In this existing development environment, `.venv/Scripts/python.exe study_server.py` is another option. The virtual environment is intentionally not included in the ZIP and should not be copied between machines.

Open http://127.0.0.1:8765 on that laptop. Keep the terminal open while reading. Press Ctrl+C to stop. This server serves files only; it does not execute notebook cells or application APIs.

## 3. Read on a mobile phone or tablet

Connect phone and laptop to the same trusted Wi-Fi. From the library folder run:

```powershell
py -3 study_server.py --lan
```

The terminal prints candidate laptop addresses such as `http://192.168.1.20:8765/`. Open the address belonging to your Wi-Fi network in the phone browser. Do not type 127.0.0.1 on the phone: that means the phone itself. On Windows, `ipconfig` shows the Wi-Fi IPv4 address if several candidates are printed. If Windows asks about a firewall rule, allow only the private network you intend to use.

The laptop must stay awake and the server must keep running. Guest Wi-Fi isolation, VPN routing or a firewall may prevent devices from connecting. Do not disable all firewall protection to work around it. Choose another port with `--port 8766` if 8765 is occupied, and use the matching port in the URL. No internet router port forwarding is needed.

LAN mode has no login and is for trusted-network reading. It blocks runtime/dependency/hidden directories and serves only allowed file types. Keep private notes or credentials outside the published learning folder. This is not a publicly hosted or TLS-protected service.

## 4. Another Windows, macOS or Linux laptop

After extraction, change to the actual folder on that device. Windows can use `py -3`; macOS/Linux commonly use `python3`:

```shell
cd /your/path/engineering-notebooks
python3 study_server.py
```

For same-Wi-Fi mobile reading use `python3 study_server.py --lan`. Reading HTML directly remains an alternative if Python is unavailable. Phone file-manager support for local linked HTML varies; serving from a laptop is the more predictable route. You can also print a chapter to PDF in the browser for offline phone reading.

## 5. Run the database and RAG exercises

The database chapter's small SQLite examples need Python's standard library. To run every executable cell in that chapter without Jupyter, use `python run_notebook_labs.py --book 29-databases-for-fullstack-and-ai` from the library root. For the RAG chapter's mathematical examples, use `python run_notebook_labs.py --book 30-rag-patterns-and-user-defined-flows`.

For an interactive notebook editor, create an environment and install JupyterLab separately:

```shell
python -m venv .venv
```

On Windows run `.venv/Scripts/python.exe -m pip install jupyterlab`, then `.venv/Scripts/python.exe -m jupyter lab`. On macOS/Linux use `.venv/bin/python -m pip install jupyterlab`, then `.venv/bin/python -m jupyter lab`. Do this in a newly extracted copy if you do not want to modify an existing environment. Select the desired .ipynb in the editor. Other chapters need their documented dependencies; Jupyter alone does not install Java, Node, ML libraries or external services.

The configurable RAG lab needs only Python in its default offline mode. From the library root:

```shell
python labs/rag-flow/test_flow.py
python labs/rag-flow/rag_flow.py --config labs/rag-flow/flow.json --question "Who leads the team maintaining Orion?"
```

On macOS/Linux substitute python3 when needed. Edit flow.json to choose the route and budgets. Actual model generation additionally requires the local Ollama service and model; these are not bundled. Read Notebook 30 and the lab README for the distinction between its transparent teaching components and production retrieval models.

## 6. Project command map

| Purpose | Working folder | Command / guide | Prerequisites |
| --- | --- | --- | --- |
| Read everything | Library root | `python study_server.py` | Python, or open index.html directly |
| Read from phone | Library root | `python study_server.py --lan` | Same trusted network and running laptop |
| Offline RAG tests | Library root | `python labs/rag-flow/test_flow.py` | Python standard library |
| Change RAG flow | Library root | `python labs/rag-flow/rag_flow.py --config labs/rag-flow/flow.json` | Edit JSON; see lab README |
| Kafka build | labs/kafka-lab | `mvn -q package` | Java 21+, Maven, initial dependency downloads |
| Native Kafka test | Library root | `python labs/kafka-lab/run.py` | Built Kafka lab; Windows runner |
| SSE/WebSocket/cache tests | Library root | `python labs/realtime-cache/test_project.py` | Tested FastAPI/httpx/websockets environment; Windows runner |
| OTLP collector test | Library root | `python labs/collector-lab/run.py` | Windows amd64, OpenTelemetry packages, first download |
| Integrated React/Java/Python app | labs/study-coach | Follow ADVANCED-RUN.md and README.md | Node, Maven/Java, Python, optional services |
| All notebook execution | Library root | `python run_notebook_labs.py` | Full documented language/dependency environment |

Native service runners that use Windows process management are not claimed cross-platform. The offline HTML and pure-Python RAG lab are portable; running every service on every OS requires the respective runtime setup. Actual container and cluster results are recorded in COMPLETION-AUDIT and the supplied JSON reports. The ZIP includes source and evidence, not dependencies, secrets or model weights.

## 7. Suggested study route

Start with START-HERE. Study database Notebook 29 before the full-stack transaction exercises. Follow Kafka 22, containers 23, Kubernetes 24, caching 25 and real-time 26. Use reliability 27 and capstone 28 to connect the pieces, then RAG 30 to design your own retrieval flow. Return to the earlier Python, Java, React, algorithms and agent notebooks whenever a prerequisite is unfamiliar.

For each lesson: explain the story aloud, trace the example, predict its output, run it, change one assumption and answer the exercise without looking. Save your own answers outside the served folder if private. Personal interview grading needs those answers; the library cannot infer your mastery from a page visit.

## Additional recovery and AI tests

See [Reliability extensions](labs/RELIABILITY-EXTENSIONS.md) for exact library-root commands for the signed durable logout relay, three-node Kafka recovery, five-minute soak, durable telemetry and pretrained/factual RAG evaluations. These are optional execution exercises; the phone reading command remains `python study_server.py --lan`. Keep private credentials and runtime files outside the reading content; the supplied server blocks runtime folders.

## Optional Windows container and cluster lab

Reading on a phone does not need Docker, Kubernetes, Java or a model. These commands are for running the infrastructure experiments on a Windows laptop with working WSL 2, sufficient free disk/memory and internet access. Start in the extracted engineering-notebooks folder. Use your Python environment with the dependencies in labs/verification-requirements.txt; setup helpers also need httpx.

```shell
python labs/setup_linux_lab.py
wsl -d EngineeringNotebookLab-13e66a98 --exec /sbin/apk add --no-cache python3 py3-redis redis docker docker-cli-compose curl ca-certificates
python labs/start_docker_lab.py
python labs/run_linux_lab.py redis
python labs/study-coach/test_containers.py
python labs/setup_k3s_lab.py
python labs/run_linux_lab.py kubernetes --capstone
```

Run these in order. The container test creates the images used by the Kubernetes capstone test. Downloads and image builds may take many minutes. These scripts create an isolated named WSL distribution and local test resources; they do not deploy to a cloud account. Check each resulting JSON report instead of assuming that installation means success. On a subsequent run, use the existing distribution and start its Docker daemon again; consult the helpers before moving the library because its virtual disk lives under .runtime.

After all tests finish, stop only this lab distribution to release memory:

```shell
wsl --terminate EngineeringNotebookLab-13e66a98
```

Do not run this stop command during a test. It does not delete the virtual disk. Do not publish .runtime or a WSL disk image; private test credentials and databases may exist there. The supplied ZIP excludes them. Keep the lighter reading server running separately when studying from your phone.
