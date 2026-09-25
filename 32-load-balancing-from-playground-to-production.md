# Notebook 32 — Load balancing: from a playground queue to production traffic

Mira runs an online cinema. At noon, tickets for a popular film go on sale. Ten customers become ten thousand. One application server is exhausted while another is nearly idle. Adding servers helped the shopping list, but nobody decided which customer should visit which counter. That is our starting problem.

This is a complete learning route through the common load-balancing decisions, with six executable Python experiments and a separate real NGINX lab. It does not claim every vendor feature has been deployed. At each stop, predict what happens before reading the explanation. The companion [production-readiness notebook](33-production-readiness-and-evidence-workbook.html) follows the same service into cloud deployment, database diagnosis, security, AI evaluation, accessibility and recovery.

## 1. Follow one request: who actually chooses the server?

Imagine a receptionist who hands each visitor a counter number. A load balancer chooses a eligible backend for a connection or request. It does not automatically fix slow SQL, incorrect payments, lost sessions or a shared database outage.

```text
Browser
  -> DNS resolution / possibly a CDN
  -> public endpoint and load balancer
  -> optional gateway / reverse proxy
  -> application instance A or B
  -> connection pool
  -> shared database / cache / broker
```

These are roles, not a requirement to buy six separate products. One proxy can provide routing, TLS termination and balancing. A reverse proxy stands in front of servers; a forward proxy acts on behalf of clients. An API gateway often adds API-specific identity, limits or transformations. A CDN caches suitable content near readers. A load balancer distributes work. Clarifying the role is more useful than arguing over overlapping product names.

**Predict:** Mira doubles application instances but the database has only ten connections available. Does capacity double? No. More callers can simply queue at the same bottleneck. Inventory the complete request path and its shared limits before scaling one box.

## 2. Layer 4 versus Layer 7: envelopes versus letters

A Layer 4 balancer typically chooses using transport information such as addresses and ports. Think of sorting sealed envelopes by destination. It can forward TCP without understanding `/payments` or a logged-in user's cookie. A Layer 7 HTTP proxy understands HTTP requests and can route `/images` to one pool and `/api` to another.

| Decision | L4 approach | L7 approach |
| --- | --- | --- |
| Routing key | Transport connection attributes | Host/path/header and other configured HTTP attributes |
| TLS | Can pass encrypted traffic through; termination depends on product/configuration | HTTP inspection normally occurs where TLS is terminated |
| Request visibility | Connection-oriented metrics | HTTP status, route and request timing |
| Long-lived traffic | One selected connection may carry much work | May balance HTTP requests/streams, but established tunnels remain attached |
| Cost/tradeoff | Less application interpretation | More policy control, parsing and configuration responsibility |

Do not equate an OSI label with an unconditional performance winner. Measure the actual implementation, encryption, connection reuse and workload. HTTP/2 can multiplex many streams over a connection: equal connection counts need not imply equal request load. A balancer distributing TCP connections can therefore look unfair at the HTTP-request level even while doing exactly what it was configured to do.

**Explain it aloud:** “We need path-based routing and HTTP observability, so an L7 proxy fits that requirement. We still need to measure capacity and decide where TLS ends.”

## 3. Round robin and weights: sharing turns fairly

Round robin cycles A, B, C, A, B, C. It is simple and useful when eligible servers have comparable capacity and requests have similar cost. But one report can take a second while another request takes a millisecond. Equal turns are not necessarily equal work.

Weights express intended relative shares. If A can handle three units while B handles one, a 3:1 policy aims for about three quarters of eligible assignments to A under its specified conditions. Weight is neither CPU percentage nor a guarantee for every short observation window. Health exclusions and existing connections affect measured traffic.

Smooth weighted round robin spreads the larger share across the sequence instead of sending a huge uninterrupted burst. In this teaching implementation, add every weight to its current score, choose the largest score, then subtract total weight from the winner. The scores act like a record of how much service each backend is owed.

```python
# lab: SmoothTicketCounters
from collections import Counter
weights={'A':3,'B':1}; current={name:0 for name in weights}; assignments=[]
for _ in range(40):
    for name,weight in weights.items(): current[name]+=weight
    chosen=max(current,key=current.get)
    current[chosen]-=sum(weights.values());assignments.append(chosen)
assert Counter(assignments)=={'A':30,'B':10}
print('First eight choices:',assignments[:8])
print('Forty requests:',dict(Counter(assignments)))
```

**Change the experiment:** set weights to 5:2:1 for A/B/C and use a request count divisible by eight. Then remove C mid-run. Decide whether to reset scores or preserve them, and document that policy. Your small scheduler is an illustration; the separate NGINX test checks a real proxy's behavior independently.

## 4. Least connections, least requests, latency and two choices

Least connections chooses the backend with fewer active connections, often with weights. It can help when connection lifetimes vary. Least outstanding requests measures a different unit. A server with one expensive report may be busier than one with ten tiny cache hits; neither count is a perfect measure of work.

A latency-aware policy can track a smoothed response estimate, but raw latency is noisy. An exponentially weighted moving average gives recent samples influence without forgetting everything: new estimate = alpha × sample + (1−alpha) × old estimate. A fast-failing server can appear “fast,” so latency must be considered alongside errors, load and health. Sampling and exploration matter when an idle backend has stale measurements.

Power of two choices samples two eligible backends and picks the less loaded one. It avoids comparing every server for every request while improving on blindly choosing one. Real systems must handle stale distributed measurements and independent balancers making simultaneous decisions.

```python
# lab: CounterSelection
loads={'A':8,'B':1,'C':4}
pair=('A','C')
choice=min(pair,key=loads.get)
assert choice=='C'  # Best sampled counter, not necessarily global best B.
estimate=100.0; alpha=.25
for sample in (100,100,500): estimate=alpha*sample+(1-alpha)*estimate
assert estimate==200.0
print('Two-choice result:',choice,'; smoothed latency:',estimate,'ms')
```

**Interview trap:** “Least connections is always best.” Ask instead: are requests short, streamed, multiplexed, CPU-heavy or sticky? Which load measurements are available? What happens when all backends are saturated?

## 5. Consistent hashing, rendezvous hashing and hot keys

Suppose each counter has a local cache. Sending the same catalogue key to the same server improves cache locality. Simple `hash(key) % server_count` remaps many keys when the count changes. A consistent-hash ring places servers and keys on a circle; virtual nodes can smooth uneven placements. Rendezvous hashing instead scores each key/server pair and chooses the largest score.

The following deterministic rendezvous example uses SHA-256 so results are stable across processes. Python's built-in hash is not an appropriate persistent cross-process routing contract because some types are randomized between processes.

```python
# lab: StableRouting
import hashlib
def owner(key,servers):
    return max(servers,key=lambda server:int.from_bytes(hashlib.sha256((key+'|'+server).encode()).digest(),'big'))
old=['A','B','C'];new=old+['D'];keys=[f'ticket-{i}' for i in range(1000)]
changed=[k for k in keys if owner(k,old)!=owner(k,new)]
assert changed and all(owner(k,new)=='D' for k in changed)
assert all(owner(k,old)==owner(k,new) for k in keys if owner(k,new)!='D')
print(len(changed),'of 1000 keys moved; changed keys moved only to the added server.')
```

This is an algorithm property test, not a production sharding system. You still need membership agreement, key encoding, weights, replication, failover and migration. Hash routing does not make a single extremely popular key disappear. One blockbuster-film key can overload its owner. Options include cached replication, request coalescing, partitioning the workload when semantics allow, or special handling for hot keys. Each trades locality for distribution.

Session affinity is related to stable routing but solves a different problem: keeping a client's requests together. Never confuse either with durable storage.

## 6. Capacity and queues: why the last few percent hurt

Mira's counter serves 100 customers per second. At 20 arrivals per second, it has breathing room. At 99, a small burst can leave a long queue. The average alone conceals the waiting customer's experience.

For a stable system, Little's law connects average in-flight work L, arrival rate lambda and average time W: L = lambda × W. At 200 requests/second and 0.25 seconds average time, about 50 requests are in flight on average. Match the observation boundary: server processing time is not the same as end-to-end time including queues.

```python
# lab: QueueCliff
service_rate=100.0
for arrival in (20.0,70.0,95.0,99.0):
    # M/M/1 illustration: Poisson arrivals, exponential service, one server, stable load.
    mean_seconds=1/(service_rate-arrival)
    in_system=arrival*mean_seconds
    assert mean_seconds>0
    print(f'{arrival:.0f}/s -> mean {mean_seconds:.3f}s, average in system {in_system:.1f}')
assert 200*.25==50
```

This queue formula is a deliberately idealized model, not a forecast for a real web service with caches, bursts and many workers. Its lesson is the shape: approaching saturation amplifies delay. If arrivals exceed sustainable service, an unbounded queue stores tomorrow's failures in memory. Bound queues, apply deadlines and reject appropriate work before collapse. A useful rejection is better than pretending an expired request is still likely to succeed. [Overload principles](https://sre.google/sre-book/handling-overload/).

For capacity planning, estimate demand after losing a failure domain. Three servers each safe at 100 requests/second provide 300 normally but only 200 after losing one. Serving 270 at normal operation is not one-server-failure capacity, even though all three currently fit the load.

## 7. Health checks: a pulse is not a completed purchase

Liveness asks whether restarting a process is likely to help. Readiness asks whether it should receive new work. Startup checks allow slow initialization. A process returning 200 from `/health` can still fail every database query; a dependency outage can also make a deep readiness check remove every server at once.

Active checks periodically probe. Passive checks infer failure from actual traffic. Use thresholds and recovery rules to avoid flapping. Record what counts as a failure: a transport timeout is not the same as a valid 404 for an absent ticket. The load-balancing lab uses NGINX passive failure handling; it does not claim an active-check feature was configured.

Imagine B is overloaded and misses health checks. Sending all B's traffic to A can overload A too. Removal is not a source of additional capacity. Pair health policy with load shedding, reserve capacity and cautious recovery. Warm caches gradually when returning a server instead of immediately giving it its full historical share.

**Fault drill:** make only a recommendation dependency fail. Should checkout become unready, or continue without recommendations? Define dependency criticality and customer-visible degradation before setting probe rules.

## 8. Sticky sessions and shared state: a favourite counter can close

A cookie or source-IP affinity rule may keep a customer on the same backend. This can reduce migration of expensive local state. It can also hide a design defect: login works until the selected server dies, then the user's in-memory session disappears.

IP affinity groups users behind a shared NAT address and may behave poorly when mobile addresses change. Cookie affinity needs lifecycle, integrity and failure behavior. Neither is authorization. A client reaching server A is not evidence that it owns account A.

Shared session storage, appropriately validated self-contained credentials, and durable revocation protocols offer different tradeoffs. A shared store can become another availability dependency. A JWT can outlive logout unless its validation/revocation design accounts for it. Persist shopping carts and payment state independently from a routing preference. Reapply identity and object authorization on every instance.

Mini incident: after scaling from one pod to two, every second refresh logs the user out. Check session storage and cookie configuration before blaming the round-robin algorithm. Stickiness might mask the symptom; it does not establish failover correctness.

## 9. TLS termination, re-encryption and the trust boundary

TLS termination means a component decrypts a connection. From that point onward, plaintext is available there. If the backend network is outside the intended trust boundary, establish another authenticated encrypted connection to the backend and verify the expected certificate identity. Two TLS connections are not one uninterrupted end-to-end session.

With passthrough, the application or downstream gateway terminates TLS; an upstream transport balancer cannot generally inspect encrypted HTTP paths. Some routing can use handshake metadata, but that is not equivalent to reading the HTTP request. Decide where certificates and private keys live, who can rotate them and how expiry is monitored.

Distinguish server identity from client identity. Mutual TLS authenticates certificate holders according to your PKI policy; application authorization still decides what an authenticated principal may do. Do not turn off hostname verification to “fix” certificate errors. Log a useful error category without exposing key material.

Our local NGINX test binds to loopback and uses generated bearer credentials. Public certificates, external TLS and managed-load-balancer configuration remain deployment exercises, not claimed local successes.

## 10. A real NGINX experiment, not just a diagram

The runnable lab starts two actual Python backend processes, A and B, plus a real NGINX process in the isolated Linux lab. It uses ephemeral loopback ports and generated credentials. It does not reuse the Study Coach database or change a public site.

From the library root on the documented Windows/WSL setup:

```shell
python labs/setup_linux_lab.py
wsl -d EngineeringNotebookLab-13e66a98 --exec /sbin/apk add --no-cache nginx python3
python labs/run_linux_lab.py load-balancing
```

On a Linux machine with nginx and Python installed, run `python3 labs/load-balancing/test_nginx.py`. Read `labs/load-balancing/test-report.json` for the actual result. Setup may need downloads; reading the notebook does not. After all lab work, Windows users can stop only this lab with `wsl --terminate EngineeringNotebookLab-13e66a98`.

The assertions check equal round-robin counts, a 3:1 weighted distribution, anonymous rejection, a sanitized forwarding header, incremental SSE delivery, non-replay of a POST after an effect and 503 response, safe GET failover when A dies, and explicit failure when both backends are gone. The test cleans up its processes. A passing report is evidence for these scenarios on one host, not a multi-region availability certificate.

The following excerpt explains the policy; the test generates a full configuration with available ports:

```nginx
upstream classroom {
    server 127.0.0.1:18181 weight=3 max_fails=1 fail_timeout=30s;
    server 127.0.0.1:18182 weight=1 max_fails=1 fail_timeout=30s;
}
server {
    listen 127.0.0.1:18180;
    location / {
        proxy_pass http://classroom;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_connect_timeout 1s;
        proxy_read_timeout 10s;
        proxy_next_upstream error timeout http_503;
        proxy_next_upstream_tries 2;
        proxy_buffering off;
    }
}
```

NGINX's exact directives and defaults depend on version and edition; the test records the installed version. Explicitly specifying HTTP/1.1 avoids relying on a changing default. Understand which failures count toward passive exclusion and when retry is permitted before copying configuration. [NGINX upstream reference](https://nginx.org/en/docs/http/ngx_http_upstream_module.html).

## 11. A dangerous retry: the payment succeeded but the response failed

At counter A, a cashier records a payment, then the receipt printer fails. Sending the same instruction to counter B can charge twice. Network retry is not a business undo button.

The lab's POST endpoint deliberately increments its effect counter and returns 503. Although the proxy can retry selected failed GET requests, it must not blindly replay this non-idempotent request on another backend after sending it. The test checks that the total effect count across A and B is one. This verifies a proxy policy boundary; it does not implement a durable payment service.

For real payments, use the durable scoped key and reconciliation protocol from Notebook 31. Account for all retry layers: browser, mobile SDK, gateway, service client and worker. Two retries at several layers can multiply downstream traffic. A deadline is an overall budget; a connect timeout or an idle read timeout is only one phase's rule. Cancellation on one side does not prove the remote business operation stopped.

**Predict:** the client times out while A is still charging the card. Should the user click “new payment”? No. Preserve the operation identity and query/reconcile its status. A load balancer can redirect future traffic; it cannot infer the missing business outcome.

## 12. WebSockets, SSE, HTTP/2 and streaming AI

An ordinary short HTTP response is like a letter. An SSE stream or WebSocket is more like a telephone call: once connected, moving later requests elsewhere does not move the existing call. Long-lived connections consume file descriptors, buffers and backend capacity. New servers receive new connections; old connections may remain unevenly distributed.

For SSE, unwanted proxy buffering can delay visible events. Configure buffering and caching deliberately, flush events, send suitable heartbeats and design a durable resume cursor when missed events matter. The real lab proves the first event reaches the client before the backend is allowed to produce the second. It does not use an arbitrary “it felt fast” assertion. [NGINX buffering behavior](https://nginx.org/en/docs/http/ngx_http_proxy_module.html).

For classic HTTP/1.1 WebSocket upgrade proxying, explicitly forward the relevant Upgrade/Connection semantics; these hop-by-hop headers are not simply forwarded like arbitrary application headers. Configure timeouts and heartbeat behavior intentionally. [NGINX WebSocket documentation](https://nginx.org/en/docs/http/websocket.html).

Reconnecting a stream needs authentication, replay policy, duplicate handling and a clear “history expired” response. A sticky session cannot reconstruct lost messages. A token expiring during a stream needs a defined closure/renewal policy. The existing real-time notebook and lab cover application-level replay and logout; this NGINX lab adds actual SSE proxy evidence, not a new claim of tested WebSocket tunnelling.

For streaming AI, measure time to first token separately from time to final answer. A responsive first token does not prove completion, correctness or fair GPU scheduling. Propagate disconnects where supported and bound abandoned work.

## 13. Kubernetes Service, Ingress, Gateway and service mesh

A Service provides a stable service-facing abstraction over changing endpoints. A LoadBalancer Service generally needs an implementation/provider to provision or integrate external balancing; writing the YAML alone does not create a working cloud endpoint everywhere. Ingress needs a controller. Gateway API introduces a richer resource model, but also needs a compatible implementation. [Kubernetes Service concepts](https://kubernetes.io/docs/concepts/services-networking/service/).

Think of Service as a stable office number and endpoints as current staff. Traffic policies, readiness, locality and session affinity influence delivery. A persistent connection can remain associated with one backend; do not expect perfectly equal HTTP request counts merely because three pods are Ready.

A service mesh can provide east-west traffic policies, identity and telemetry. It adds configuration, resource and failure complexity. It cannot make an unsafe debit retry safe. Choose it for concrete requirements that justify operating it, not because a diagram looks more advanced with sidecars.

Trace the actual path: cloud frontend → ingress/gateway implementation → service/backend endpoints → pod. Avoid unnecessary proxy layers with conflicting timeouts and duplicate retries. When investigating imbalance, inspect connection reuse, endpoint membership, sticky policy, zone locality and measured request cost before changing algorithms.

## 14. Autoscaling and cold starts: more counters take time to open

Balancing distributes existing eligible capacity. Autoscaling changes capacity. They are related, but one does not substitute for the other. New pods need scheduling, image availability, initialization, readiness and often cache warm-up before they can help.

CPU utilization can be a poor scaling signal for a service blocked on a database or serving many idle sockets. Consider request concurrency, queue age, latency and dependency limits. Scaling a connection pool from ten replicas to a hundred can exhaust a database even if each replica keeps the same small pool.

Use minimum capacity, stabilization, appropriate resource requests and controlled scale-down. Choose a target below overload and test the reaction delay against expected bursts. A ten-second burst is not solved by a two-minute capacity startup unless buffering/rejection protects the system in the meantime.

**Worked estimate:** normal demand is 1,200 requests/second and each instance is comfortable at 200. Six instances fit steady demand, but seven are needed to retain 1,200 after losing one, before extra headroom and deployment overhead. If readiness takes a minute, capacity planning must cover that minute too.

## 15. Draining, rolling releases and graceful shutdown

To close a counter politely, stop sending new visitors, let current visitors finish within a deadline, and handle unfinished work explicitly. Removing an endpoint and stopping its process are not necessarily simultaneous at every proxy and client.

```python
# lab: DrainTheCounter
state={'accepting':True,'active':2}
def admit():
    if not state['accepting']: return False
    state['active']+=1;return True
state['accepting']=False
assert admit() is False
state['active']-=1;assert state['active']==1
state['active']-=1;assert state['active']==0
print('No new admissions after drain; existing work reaches zero before stop.')
```

This state-machine illustration does not emulate a proxy's drain implementation. Production checks must include propagation delay, idle keepalive connections, long-lived streams, worker leases, termination grace periods and hard deadline behavior. A pre-stop delay alone is not proof every layer stopped routing traffic.

During a rolling release, ensure old and new code understand overlapping API/event/database schemas. Expand, migrate, switch, then contract. If new code deletes a column the old version needs, an application rollback may be impossible. A canary compares a small eligible population against a baseline; compare errors, latency and business outcomes, not just pod readiness. Blue/green routing permits a quick traffic switch but still shares the database compatibility problem.

## 16. The balancer can fail too: DNS, zones and regions

Two backends behind one unprotected proxy still depend on that proxy. Managed or replicated balancing can reduce that failure point, but you must understand its control plane, state, zone capacity and recovery behavior. A local lab with several processes does not survive loss of its laptop.

DNS distributes answers with caching, TTLs and client-specific behavior. Changing a DNS record does not instantly move every established connection or cached client. Anycast advertises an address from multiple locations and depends on network routing; it is not a guarantee that every request selects the lowest application latency. Global traffic policies must coordinate with where data can safely be read or written.

Active/passive designs can simplify single-writer state but require verified promotion and fencing. Active/active can improve locality and availability but introduces conflict and consistency design. Do not send writes to two independently promoted primaries unless the data model explicitly supports it. A regional endpoint becoming reachable is not proof its database is current enough to accept financial writes.

## 17. Forwarded headers, rate limits and abuse boundaries

Behind a proxy, the immediate network peer is often the proxy itself. Applications sometimes use forwarded headers to recover the original client address or scheme. Only trust headers set or sanitized by a known, protected proxy path. A client-supplied `X-Forwarded-For: 127.0.0.1` is not proof of localhost privilege.

The lab overwrites X-Forwarded-For at its single edge and verifies a forged value is replaced. A multi-proxy chain needs an explicit trusted-hop policy rather than blindly dropping or trusting every address. Authentication and tenant authorization must not be delegated to an arbitrary header.

Rate limits differ from concurrency limits. A tenant sending a few extremely slow requests can occupy all workers while staying under requests-per-second limits. Bound body/header sizes, connection duration and per-dependency concurrency where appropriate. Preserve protocol correctness; custom HTTP parsers and inconsistent proxy/backend parsing can create request-smuggling risks. Use maintained implementations and test the configured chain.

## 18. Observability: explain the queue without guessing

Collect request rate, eligible backend count, outstanding work, errors, rejection counts, queue time, backend connection time, response time and end-to-end latency. Separate 4xx due to client behavior from proxy transport failures and backend 5xx. Averages hide tail latency; inspect p95/p99 alongside volume and sample size.

```python
# lab: PercentileTrap
times=[10]*95+[1000]*5
mean=sum(times)/len(times)
ordered=sorted(times)
def nearest_rank(p):
    import math
    return ordered[max(0,math.ceil(p*len(ordered))-1)]
assert mean==59.5 and nearest_rank(.99)==1000
print('Mean:',mean,'ms; p99:',nearest_rank(.99),'ms')
```

Record which percentile definition and interval you use. Do not average percentiles from different servers as if that produced the combined percentile. Do not put raw user IDs, prompts or request IDs into unlimited metric labels; use bounded labels and traces/logs with appropriate retention and privacy controls.

When B gets little traffic, follow a diagnostic order: is it ready and present? Does it have a lower weight? Is affinity pinning traffic? Are existing connections persistent? Is passive health exclusion active? Does locality constrain selection? Are metrics measuring connections or requests? Only then decide whether the algorithm itself is wrong.

## 19. Interview challenge and answer key

Design Mira's ticket API for a sudden 10× burst. It has short catalogue reads, a payment POST and live status streams. One server dies halfway through a payment; another deployment begins while streams remain open.

Award two points each for: workload-specific routing; bounded queues/deadlines; spare capacity and autoscaling delay; durable idempotency/reconciliation; correct stream resume; shared state/authorization; readiness versus liveness; drain/rollback compatibility; trusted headers/TLS; evidence-driven metrics. A strong answer scores at least 16/20 and never treats an ambiguous payment timeout as a guaranteed failure.

Worked outline: cache authorized/public catalogue data appropriately; use healthy L7 backends for HTTP policy; keep payment intent in durable storage; retry only within the business contract; retain status events with cursors; avoid relying on sticky sessions for correctness; reserve failure capacity; drain old instances with a deadline and resume policy; compare canary business outcomes; inspect tail latency and saturation.

Your answer can choose different products or algorithms if its assumptions, invariants and failure behavior are clear. The goal is to explain why the system remains understandable when something breaks, not to draw the largest collection of boxes.

## 20. What was explained, simulated and executed

Six notebook cells explore weighted scheduling, sampled choices/EWMA, rendezvous hashing, queue behavior, draining and percentiles. They are deterministic teaching experiments. The NGINX lab separately tests a real local reverse proxy and two backend processes; consult its report for actual results. TLS deployment, L4 balancing, public ingress, WebSocket tunnelling and independent-host failure are explained but not newly certified by that test.

Continue with Notebook 33 for the cloud deployment acceptance plan, AI-quality scorecards, database plan exercises, accessibility scenarios, identity rotation, disaster recovery and a personal interview schedule. This distinction between understanding, simulation and executed evidence is itself an interview skill.
