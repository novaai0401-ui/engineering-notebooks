# 26 — Real-time applications: messages that survive disconnection

## 1. Choose the conversation shape

Polling is repeatedly asking “Is it ready?” SSE is a teacher continuously announcing updates to listening students. WebSocket is a telephone conversation in which both sides can speak. Choose by interaction needs, network constraints and recovery requirements rather than treating newer protocols as automatically better.

| Mechanism | Direction | Useful example | Main design work |
| --- | --- | --- | --- |
| Polling | Client request/server response | Infrequent job status | Interval, conditional requests, load |
| Long polling | Delayed HTTP response | Compatibility fallback | Timeouts, repeated requests |
| SSE | Server to client over HTTP | AI tokens, progress, notifications | Replay cursor, proxy buffering, reconnect |
| WebSocket | Bidirectional | Collaborative interaction, chat | Protocol, heartbeat, bounded queues, reconnect |

An open connection is not guaranteed delivery. Every method needs authentication, authorization, resource limits and a recovery policy.

## 2. SSE framing and the browser

An SSE response uses `text/event-stream`. Each event is separated by a blank line. `data:` carries payload, `event:` can name the event type and `id:` supplies a reconnect cursor. Comments can serve as heartbeat traffic. Native EventSource reconnects and can send Last-Event-ID; the server must implement meaningful replay. [SSE guide](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events).

```text
id: 42
event: progress
data: {"job":"job-7","status":"complete"}

```

Native browser EventSource does not provide arbitrary request-header configuration like fetch. Same-origin cookies are one option; streaming fetch permits other request handling but needs a parser and reconnect implementation. Do not place long-lived bearer secrets in query strings. Browser cookies require a deliberate same-origin/cross-origin and CSRF policy for related mutations.

## 3. Replay, gaps and duplicate delivery

If the client received event 42 but lost its acknowledgement or disconnected before recording it, replay can repeat 42. Deduplicate by stable event ID or make state application idempotent. If the server retained only events 80 onward and the client asks after 42, silently starting at 80 hides missing state. Return a defined resynchronization signal and fetch an authorized snapshot.

```python
# lab: stream_replay_and_gap
events=[(n,{'count':n}) for n in range(8,13)]
def replay(after):
    if after<events[0][0]-1:raise ValueError('Snapshot required')
    return [(n,payload) for n,payload in events if n>after]
assert [n for n,_ in replay(10)]==[11,12]
try:replay(3)
except ValueError:pass
else:raise AssertionError('History gap hidden')
state={}
for event_id,payload in replay(10)+replay(10):state[event_id]=payload
assert len(state)==2
print('Replay is duplicate-safe and refuses a silently incomplete history.')
```

The snapshot and cursor must describe a consistent point. If you fetch a snapshot and then start listening after an unrelated current cursor, you can miss updates between them. Obtain a revision with the snapshot and replay after that revision, or implement an equivalent atomic handoff.

## 4. WebSocket protocol and security

After the handshake, define message types, version, maximum size, request ID, validation rules and error responses. A WebSocket handshake authenticated by cookies is still vulnerable to unwanted cross-site use unless the server validates allowed Origin and the identity/authorization model. Origin checking complements authentication; non-browser clients can choose their own Origin header.

Revalidate session expiry and permissions during long connections or close them on revocation. Authorize each room/job subscription and mutation. Never trust a message's user_id as identity. Reject malformed messages without leaking server internals. Keep binary/text encoding and maximum decompressed sizes explicit. The browser WebSocket API does not automatically solve application backpressure. [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API).

## 5. Heartbeats, backpressure and cancellation

A dead network path can leave a seemingly open connection. Heartbeats and deadlines detect it. Bound queued bytes per client; if a client cannot keep up, disconnect with a resync path or coalesce replaceable state. Never let one slow reader accumulate an unbounded list of model tokens.

Cancelling the browser connection should stop unnecessary generation where supported, release server resources and preserve a truthful job state. Some upstream operations cannot be cancelled after acceptance; distinguish “stop displaying” from “the effect did not occur.” A retry needs the same logical operation ID if duplication would matter.

## 6. Scaling across application instances

A browser is connected to one server instance. That instance needs the events relevant to its clients. If all instances share one Kafka consumer group, each partition is owned by one consumer; every instance does not receive every event. Choose a fanout topology deliberately: route subscriptions to the owning instance, use a fanout tier, or use distinct consumption arrangements with an understood cost.

Redis Pub/Sub can notify live instances but cannot replay after disconnection. Persist a durable cursor source when recovery matters. Load-balancer idle timeouts, proxy buffering, HTTP version, connection limits and rolling shutdown affect behavior. A sticky session is not durable event storage.

## 7. React and Spring integration

In React, create the connection in an effect and close it in cleanup. Abort pending fetches on teardown, avoid stale closures, deduplicate events and expose reconnecting/stale states accessibly. Keep rapidly arriving tokens from triggering excessive renders by batching display updates. Do not announce every token to a screen reader; announce meaningful status changes and provide the complete answer for reading.

In Spring MVC, SseEmitter needs timeout/error/completion cleanup and a bounded execution strategy. WebFlux can represent streams with Flux, but backpressure only works where the complete chain honors it. STOMP adds a messaging protocol on WebSocket; destinations still need authorization, and broker relay configuration is not equivalent to durable application storage. Choose one coherent implementation before layering frameworks.

## 8. Run the included real project

`labs/realtime-cache/app.py` is a separate FastAPI/SQLite project with a simple browser page. It supports cookie login, CSRF-protected HTTP writes, SSE replay, authenticated WebSocket publish/ping, logout-driven socket closure, owner-scoped ETags and idempotent writes. Start it using its README rather than importing it into the Study Coach application.

The native test opens an actual WebSocket, rejects an unwanted Origin, publishes an event, logs out and checks closure. It checks SSE Last-Event-ID replay, a retention gap, concurrent writes and recovery after process restart. In-memory sessions intentionally disappear on restart; durable messages remain. This is a local single-process teaching project, not a multi-instance production certificate.

Six additional browser journeys passed across Chromium, Firefox and WebKit at desktop and narrow widths, including keyboard use and axe checks. A further four-client recovery test killed the process during writes, reauthenticated after restart and retried stable keys: eighty acknowledged logical writes matched eighty durable events. The reports record actual scope and duration; a short forced outage does not prove long endurance.

## 9. Interview/debugging round

“AI responses arrive all at once instead of streaming.” Investigate server flushing, proxy buffering, content type, client parsing and upstream streaming. “After reconnect, messages repeat.” Examine stable IDs and idempotent application. “Some users never see events with two servers.” Examine consumer-group topology and subscription routing. “A logged-out user keeps receiving updates.” Examine long-connection revocation, not just the HTTP login endpoint.

For each bug, write a reproducer, identify the invariant, patch the responsible layer and repeat under disconnect/restart. A happy-path animation is not a reliability test.

## 10. Two real application instances

The added test_multi_instance.py starts two separate FastAPI processes sharing a SQLite WAL journal. A write sent to instance A is observed by a WebSocket and an SSE connection on instance B. B also notices the new database revision instead of returning its earlier cached representation. This is polling-based fanout through a shared journal, not Redis pub/sub or a distributed streaming platform.

The test exposed a design issue worth remembering: a lock inside A cannot stop B. If both read maximum sequence 4, both might try to write sequence 5. The write transaction now uses BEGIN IMMEDIATE before reading the sequence and idempotency record. SQLite reserves the writer slot; the next writer reads the committed result before deciding what to do. Database uniqueness constraints remain the final guard.

Two simultaneous submissions of the same logical key returned one durable sequence, and eighty distinct cross-instance writes had eighty distinct sequences. The original single-instance protocol tests also passed after this change. Sessions remain separate and in memory. Independent hosts, shared authentication and larger fanout need a different deployment design; these limits do not invalidate the local concurrency lesson.
