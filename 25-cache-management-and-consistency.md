# 25 — Cache management: keeping photocopies useful

## 1. A cache is a photocopy with a promise

The school register is authoritative; a teacher keeps a photocopy to answer questions quickly. When the register changes, the photocopy can be wrong. Before choosing Redis or Caffeine, decide which answers may be stale, for how long, and what the UI should disclose. A cached public course description and a cached account-permission decision have different consequences.

Cache-aside means the application checks the cache, loads on a miss and stores the result. Read-through delegates loading to a cache abstraction. Write-through updates through a coordinated cache layer before acknowledging according to its contract. Write-behind defers durable writes and therefore needs a durable queue/recovery design if losing accepted writes is unacceptable. A cache is not inherently durable storage.

## 2. Keys, ownership and scope

A key should include all dimensions that affect the answer: tenant, resource, relevant permissions, locale and schema/version where applicable. Caching /profile under one global key leaks data even if the database query was correctly authorized. Avoid logging personal data in keys. Invalidate cached authorization when its authority changes, or explicitly bound how long it may remain accepted.

Local caches are fast but each process has its own copy. Redis gives multiple processes a shared service and additional network/failure costs. A CDN caches at the edge; browser HTTP caching follows response directives. These layers can disagree unless you specify policy end to end.

## 3. TTL, eviction and capacity

TTL expires entries after time; eviction frees capacity. LRU removes least recently used entries, LFU favors frequency, and size-aware admission can reject expensive low-value objects. Redis offers configurable policies; do not assume its approximate eviction implementation is identical to a textbook perfect LRU. A TTL is a maximum local residence under a policy, not proof of global freshness after a remote write.

```python
# lab: cache_lru_and_ttl
from collections import OrderedDict
class Cache:
    def __init__(self,capacity): self.data=OrderedDict();self.capacity=capacity
    def put(self,key,value,now,ttl):
        self.data[key]=(value,now+ttl);self.data.move_to_end(key)
        while len(self.data)>self.capacity:self.data.popitem(last=False)
    def get(self,key,now):
        if key not in self.data:return None
        value,expires=self.data[key]
        if now>=expires:del self.data[key];return None
        self.data.move_to_end(key);return value
c=Cache(2);c.put('a',1,0,10);c.put('b',2,0,10)
assert c.get('a',1)==1
c.put('c',3,1,10)
assert c.get('b',2) is None and c.get('a',10) is None
print('Capacity evicted b; time expired a.')
```

This toy cache is single-threaded, uses entry count rather than bytes, and conflates cached None with a miss. Production APIs need an explicit hit/miss representation and synchronization policy.

## 4. Invalidation and the late-loader race

Deleting a key after a database commit avoids deleting on rolled-back writes, but a concurrent old reader can refill it with old data afterward. Sequence: reader loads version 4; writer commits version 5 and invalidates; reader finally puts version 4. A version fence must reject older fills even when the value was deleted. Store the fence long enough, or revalidate against the authority.

```python
# lab: cache_version_fence
fence={'course':4};cached={}
def put(key,version,value):
    if version<fence.get(key,0):return False
    fence[key]=version;cached[key]=(version,value);return True
old_read=(4,'old title')
fence['course']=5;cached.pop('course',None)
assert not put('course',*old_read)
assert put('course',5,'new title')
print(cached)
```

In a distributed implementation, compare-and-set must be atomic, for example through a carefully tested Redis script or transaction. Reading a fence then writing separately recreates a race. Event invalidation is delayed and can be duplicated; track versions and define what happens after a missed event. The included real-time lab rechecks the database revision on snapshot reads, so it caches the projection rather than avoiding every database access.

## 5. Stampedes, avalanches and penetration

A stampede is many requests rebuilding one expired key. Single-flight lets one loader run while others await a bounded result. TTL jitter spreads expiration across keys. Negative caching can briefly remember a genuine absence, but must not mix authorization failures across users or permanently hide newly created records. An avalanche is many keys expiring together or an entire cache becoming unavailable.

Define fallback capacity. Sending every missed request directly to a fragile database can cause a cascading outage. Use bounded concurrency, deadlines, admission control and, where acceptable, explicitly labelled stale data. Never substitute stale permission or inventory guarantees without a business-approved consistency model.

## 6. Redis locks and leases

A lease expires, but the old holder may continue running after a pause. A token-checked atomic delete prevents one holder from deleting another's lock; it does not stop the paused holder from writing to a separate database. A monotonically increasing fencing token enforced by the protected resource can reject stale holders. Explain the failure model before presenting a distributed lock as mutual exclusion under every possible failure.

Redis Pub/Sub offers live message delivery to connected subscribers, not a durable replay log. Redis Streams has different retention, consumer and acknowledgement semantics. Persistence, replication and failover settings affect data-loss windows. Treat a rate limiter, session store and disposable cache as different workloads, even if all use Redis. [Redis client cache principles](https://redis.io/docs/latest/develop/reference/client-side-caching/).

## 7. Spring and Python integration

Spring @Cacheable expresses read caching; @CacheEvict expresses eviction. Specify the cache manager, key, serialization, TTL and transactional timing rather than assuming annotations choose them correctly. Proxy interception means self-invocation can bypass annotation behavior. Caffeine is local memory; selecting it does not broadcast invalidations to another replica.

Python can wrap a loader with a bounded cache or use a Redis client with connect/read timeouts, pool limits and serialization validation. Never unpickle untrusted cache values. Treat cache errors explicitly, and observe hit ratio, misses, evictions, bytes, load duration and backend pressure. A high hit ratio can coexist with terrible p99 latency or stale wrong answers.

## 8. HTTP caching and ETags

An ETag identifies a representation version. A client sends If-None-Match; the server can return 304 when the current authorized representation matches. Authorization still runs before deciding that the cached representation is valid. `private` limits shared-cache storage; `no-cache` means revalidate before reuse, while `no-store` forbids storing under the directive's rules.

Personal responses need deliberate cache headers and Vary handling where relevant. An ETag should cover every representation-changing input, not just one table timestamp. The real-time lab tests per-user ETags, mutation invalidation and conditional reads. It does not claim to test Redis failover.

## 9. Working project and interview drill

Read `labs/realtime-cache/app.py`, run `test_project.py`, then inspect `report.json`. Its bounded local cache tests TTL, LRU and stale-version rejection; HTTP tests exercise ownership, ETags and invalidation. The same app exposes real SSE and WebSockets, making cache/stream consistency observable.

Interview: after a write, one user sees stale data for ten minutes. Trace browser cache, CDN, server cache, read replica and database transaction in order. Check cache keys and revision propagation. Propose a measured freshness contract and a regression test rather than immediately increasing TTLs or flushing every customer's cache.

## 10. Actual Redis failover: electing a replacement captain

The new Linux lab runs three Redis servers and three Sentinel processes with generated passwords. Imagine one captain recording changes and two helpers copying the notebook. Three supervisors watch the captain. When the captain stops, the supervisors can agree on a replacement, and a Sentinel-aware client asks where to send its next write.

The test first waits for both replicas to acknowledge a record. It then kills the primary process, waits for promotion, reads the earlier record through the client, writes new data and checks a cache entry expires. Finally, it restarts the old primary and verifies that it becomes a replica and catches up. The recorded run used Redis 8.0.4 and passed these checks.

This does not turn Redis replication into synchronous consensus. WAIT measures acknowledgements in that execution; asynchronous replication can still lose data under other failures. A three-process election on one computer is not a three-machine resilience test. Distinguish Sentinel's failover coordination, the client's rediscovery and the durability of your business data. A cache can often be rebuilt; an authoritative payment ledger needs a separately justified durability design.

Run `labs/test_redis_failover.py` inside the named WSL lab using the exact commands in [Reliability extensions](labs/RELIABILITY-EXTENSIONS.md). No cloud account is required for this local exercise.
