# Observability runbook

Set `COACH_TRACE_FILE` to a different writable JSONL file for each process. Java creates job spans and sends W3C trace context to Python; Python records request spans. `test_distributed.py` asserts trace and parent-span links. Never point concurrent processes at one output file.

Set `COACH_OTLP_ENDPOINT=http://collector:4318` to enable optional OTLP HTTP export. `collector.yaml` is a reference collector pipeline, not an executed collector deployment. Bind collector ingestion to a private network and add authentication/TLS before exposing it across trust boundaries.

Java `/actuator/prometheus` requires the OIDC administrator role. Python `/metrics` requires `Authorization: Bearer <COACH_SERVICE_TOKEN>`. A production Prometheus scraper needs a dedicated service identity: do not distribute a person's browser session or reuse a highly privileged administrator password. Configure that identity in the chosen infrastructure before enabling scraping.

`alerts.yaml` contains example PromQL rules. The monitoring harness loads them into native Prometheus and uses promtool to validate syntax and a timed firing fixture in `alert-tests.yaml`. HTTP status metrics alone miss errors that occur after a streaming response starts; inspect job failure counters and terminal job outcomes as well. `monitoring-report.json` and `monitoring-dashboard.html` record the observed scrape and query result; the dashboard is a saved snapshot.

Use `distributed-report.json` for the measured local 12-job load exercise. Its p95 is the maximum of a very small sample, not a reliable production percentile. First compare queue wait, inference time and database time; then investigate saturation of connection pools, model memory and worker capacity. Do not scale blindly.

Runbook: identify the affected user outcome; inspect bounded error/latency metrics; find correlated trace IDs; classify dependency failure versus invalid input; stop retry storms; recover the dependency; replay only after verifying idempotency; record the observed recovery time and remaining data-loss risk.
