# Real OTLP collector smoke test

From the library root run `.venv/Scripts/python.exe labs/collector-lab/run.py` on Windows amd64. The runner downloads the pinned official OpenTelemetry Collector 0.161.0 archive, checks its SHA-256, validates a minimal config and launches it on loopback 14318. Python exports a real span using OTLP/HTTP; the test checks the collector debug output for its trace ID and name, then stops the owned process.

Downloads, configuration and logs stay under excluded .runtime. The recorded report is deliverable evidence. This does not test Grafana, a durable trace backend, TLS/authentication, sampling policies or outage buffering. The test requires internet only for the first download and uses the library's installed OpenTelemetry packages.

In a fresh environment, install the tested top-level dependencies from the library root with `python -m pip install -r labs/collector-lab/requirements.txt`. The pins are not a complete transitive lockfile.
