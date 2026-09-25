# Completion audit: implemented work and verified boundaries

Updated 25 September 2026. 33 notebooks cover the requested curriculum. This audit separates implemented lessons, executed local tests and acceptance checks requiring your environment or participation. It does not promise every possible exam or algorithm.

## Completed local work

| Area | What actually ran | Evidence |
| --- | --- | --- |
| Notebook exercises | 153 recorded passing executable cells; 33 reading notebooks | [Validation](VALIDATION.html) |
| Interview expansion | Java/Spring questions, SOLID/GoF and microservice patterns, pagination, MySQL/Oracle diagnostics, Batch restart and testing | [Notebook 31](31-java-microservices-interview-masterclass.html), [Spring workshop](labs/interview-workshop/test-report.json) |
| Load balancing | Real NGINX with two backend processes: round robin, weights, authorization, forwarding headers, SSE, POST retry safety and backend loss | [NGINX report](labs/load-balancing/test-report.json), [Notebook 32](32-load-balancing-from-playground-to-production.html) |
| Docker | Current recorded result: **passed**. Supplied multi-stage images, authenticated Java/Python job, approval, idempotency, SSE and volume restart test | [Container report](labs/study-coach/container-report.json) |
| Kubernetes | Current recorded result: **passed**. Actual K3s node, pod replacement and scaling; capstone Services, Secret and persistent volume checks | [Cluster report](labs/kubernetes-report.json) |
| Redis | Three actual servers and three Sentinels; primary killed, replacement discovered, data/write/TTL checked, old primary rejoins as replica | [Redis report](labs/redis-failover-report.json) |
| Identity | Post-mitigation ten fresh logins and forty anonymous probes passed. Real Keycloak/Spring durable logout survives relay restart while a receiver is network-unavailable | [Login report](labs/study-coach/identity-repeat-report.json), [durable delivery](labs/study-coach/durable-spring-report.json) |
| Kafka | Three real broker processes; leader loss, further acknowledged writes and recovered in-sync replicas | [Cluster report](labs/kafka-lab/cluster-report.json) |
| Real-time/cache | Two actual processes share durable state: cross-instance SSE/WebSocket delivery, changed ETags and concurrent idempotency/sequence allocation | [Two-instance report](labs/realtime-cache/multi-instance-report.json) |
| Endurance/recovery | Ten-minute rerun: 2,678 writes and 8,035 requests, with memory/handle samples. Original five-minute soak and separate crash/retry experiment retained | [Ten-minute report](labs/realtime-cache/endurance-600-report.json), [recovery](labs/realtime-cache/recovery-report.json) |
| Telemetry | Real collector persists queued spans across its crash; SQLite destination retains committed spans across restart | [Persistent queue report](labs/collector-lab/persistent-report.json) |
| Pretrained RAG | Actual MiniLM encoder: twelve relevance and four ownership cases; configurable retrieval and bounded model-selected search | [Retrieval report](labs/rag-flow/pretrained-report.json), [integration](labs/rag-flow/model-integration-report.json) |
| Graph pipeline | Actual model extracts relationships, then provenance/ACL checks, SQLite persistence, multi-hop traversal, communities, updates and deletion run | [Graph report](labs/rag-flow/graph-pipeline-report.json) |
| Generation failure handling | Timeout/connection/malformed-output faults return clearly labelled authorized excerpts; no-evidence requests skip generation | [Recovery tests](labs/rag-flow/generation-recovery-report.json) |
| Reading/accessibility automation | Desktop/narrow reading layouts, selected keyboard journeys and automated accessibility checks; portable archive smoke tests | [Layout report](reading-layout-report.json), [portable report](portable-report.json) |

Raw reports preserve limitations and failed attempts. Follow [Reliability extensions](labs/RELIABILITY-EXTENSIONS.md) to reproduce advanced checks. The Docker and Kubernetes rows display actual report status, not an assumption that a recipe passed.

The first Kubernetes attempt exposed a loopback-only API listener that blocked in-cluster DNS/storage services. The listener was corrected and system-service readiness made an explicit gate. A subsequent startup race required waiting for system Deployments to exist before checking rollout. [Initial evidence](labs/kubernetes-initial-report.json) and [diagnosis](labs/kubernetes-initial-review.json) remain available. The latest report determines the final result.

## AI quality is still an open limitation

The original strict eight-case factual baseline passed five; tutor review identified one additional semantically correct answer, one unnecessary abstention and one timeout. The baseline has not been overwritten. A bounded injection retest subsequently answered correctly in 34.61 seconds. However, the broader revised **development** regression passed **six of eight**: an entity answer over-abstained and the absent-evidence case timed out. Reused questions are not an independent holdout, and a passing citation or retrieval check does not prove an answer is true.

[Original baseline](labs/rag-flow/factual-holdout-report.json), [bounded retest](labs/rag-flow/bounded-generation-report.json), [development regression](labs/rag-flow/development-regression-report.json). Earlier incorrect Study Coach generation remains in its factual review. Extractive output stays the default. The new fallback repairs availability during generation failure; it does not repair arbitrary model reasoning. Broader independent factual adjudication remains needed before relying on generated answers without review.

## Acceptance work that still requires input or access

The written curriculum now covers each previously pending area in [Notebook 33: production readiness](33-production-readiness-and-evidence-workbook.html). The MySQL/Oracle scripts are supplied but have not been run on those engines. Multi-host, public TLS, longer-duration and provider-specific recovery checks remain bounded by the target environment. Added explanations and simulations are not relabelled as external acceptance.

Hosted CI for prior commit bc63933215c492cfe2e2a9edd2f2cd1e87111443 passed: [GitHub run](https://github.com/novaai0401-ui/engineering-notebooks/actions/runs/36097858718). This closes the previously unchecked result for that exact commit. New commits require their own CI result; this statement is not a claim about an unobserved run.

1. **Actual public-cloud deployment:** provide the authorized account/project, region and spending limit. Local Docker/K3s execution is real, but it is not a cloud rollout. No destination or budget has been supplied.
2. **Physical-device and manual screen-reader audit:** use an actual device with Safari/VoiceOver or the chosen mobile browser/screen reader and record the tasks in [Manual acceptance](labs/MANUAL-ACCEPTANCE.md). Desktop WebKit and narrow viewports cannot establish physical iPhone behavior.
3. **Personal interview grading:** submit the unaided answer and elapsed time from that same worksheet. No personal score can be assigned before observing your work.

These remain open, not silently marked completed. The tutorial package is usable now, but full external acceptance and general AI accuracy are not certified.

## Practical scope of the local evidence

All broker, Redis and cluster nodes share one computer/VM. Tests do not certify independent-host partitions, disk destruction or multi-day endurance. H2 uses one writer and Kubernetes Recreate with a local persistent volume; scaling this profile to multiple database writers is not supported. Cloud ingress, production OIDC deployment and production storage require destination-specific configuration.

The identity receiver was unavailable through a 503 proxy while its real Spring session stayed alive; it was not an application-process crash with shared sessions. The historical intermittent-login root cause remains a hypothesis, even though the mitigation passed repeated checks. Expired-token reconciliation and zero-downtime secret overlap are not claimed. Initial failing evidence is retained.

The graph pipeline is a small custom implementation, not Microsoft GraphRAG. Normalized name matching is not full entity resolution; extractive community summaries and quote-presence validation are not factual entailment proofs. The original offline RAG routes remain intentionally transparent teaching components alongside separately tested real integrations.

## Study on laptop or mobile

Extract Engineering-Notebooks.zip and open engineering-notebooks/index.html for offline reading. From that folder, run `python study_server.py` for laptop HTTP access or `python study_server.py --lan` on trusted Wi-Fi for phone access. The server prints the addresses. Keep the laptop running. Detailed setup, optional service commands and lab shutdown are in [Laptop and mobile commands](STUDY-ON-ANY-DEVICE.html).

Model weights, dependencies, private credentials, runtime databases and the WSL virtual disk are excluded from the reading archive. Reading needs no external website; executing optional frameworks and infrastructure requires the listed installed runtimes and initial downloads.
