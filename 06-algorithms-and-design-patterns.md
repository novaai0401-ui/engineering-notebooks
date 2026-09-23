# Notebook 6 — Algorithms, Design Principles, and Patterns

This companion builds interview problem-solving skills across Python, Java, frontend, and AI engineering. It contains detailed lessons for recurring algorithm techniques, a complete catalog of the **23 classic Gang of Four patterns**, selected architecture patterns, worked code, and exercises. “All 23 GoF patterns” is a bounded claim; it does not mean all patterns or algorithms ever invented.

## 1. How to solve a problem before coding

Imagine organizing numbered library cards. First ask what answer is required, whether duplicates exist, how much data there is, and whether the cards are already sorted. A fast method based on an untrue assumption is not a solution.

Define inputs, outputs, invalid cases, and constraints. Work a tiny example. Write a correct simple approach. State an invariant: something true before and after each step. Then improve time or memory if constraints require it. Test empty, singleton, duplicate, boundary, and adversarial cases.

Big-O describes growth, not seconds. O(n) scans n items; O(log n) repeatedly shrinks the search region by a constant factor; O(n log n) often appears in efficient comparison sorting; O(n squared) checks many pairs. Space complexity includes auxiliary storage and recursion depth under your stated convention.

**Example:** A ten-item linear scan can beat a complicated indexed approach whose setup dominates. Explain workload and reuse, not just asymptotic notation.

## 2. Data structures as containers with promises

An array provides indexed positions. A dynamic array occasionally reallocates; appending is commonly amortized O(1), not a guarantee that every append costs the same. A linked list changes connections cheaply when the relevant node is known, but searching still takes work.

A stack removes the newest item first, like stacked plates. A queue removes the oldest first, like a lunch line. A deque works at both ends. A hash map stores key/value associations with expected fast lookup under suitable hashing assumptions; worst-case behavior and implementation protections vary. A balanced search tree supports ordered operations in logarithmic time. A heap efficiently exposes an extremal item but does not keep all entries in sorted order.

A trie stores shared prefixes, useful for autocomplete. A graph stores vertices and edges, representing relationships or transitions. A disjoint-set structure tracks which items belong to the same connected group. Select a structure based on operations, not familiarity.

## 3. Hash lookup: find a pair without checking every pair

For numbers [2,7,11,15] and target 9, the answer uses 2 and 7. Instead of comparing every pair, remember earlier values and ask whether the complement has appeared.

```python
# lab: two_sum
def two_sum(numbers, target):
    seen = {}
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in seen:
            return seen[complement], index
        seen[value] = index
    return None

assert two_sum([2,7,11,15], 9) == (0,1)
assert two_sum([3,3], 6) == (0,1)
assert two_sum([1], 2) is None
print("Pair indices found without reusing one item")
```

The invariant is that `seen` contains only earlier indices. Checking before insertion prevents using one item twice. Expected time is O(n), auxiliary space O(n), with ordinary hash-table assumptions. Decide how to handle multiple valid answers; this returns the first found under its traversal.

## 4. Two pointers and sliding windows

Two pointers move through data while preserving a relationship. For a sorted array and target sum, compare endpoints. If their sum is too small, advance the lower pointer; if too large, decrease the upper pointer. Sorted order justifies eliminating candidates.

A sliding window tracks a contiguous region. Grow the right edge and shrink the left when a condition is violated. It works when the update and shrink rules preserve a useful invariant; not every optimization problem has that structure.

```python
# lab: longest_unique_window
def longest_unique(text):
    last = {}
    left = best = 0
    for right, character in enumerate(text):
        left = max(left, last.get(character, -1) + 1)
        last[character] = right
        best = max(best, right - left + 1)
    return best

assert longest_unique("abba") == 2
assert longest_unique("") == 0
assert longest_unique("abcabcbb") == 3
print("Longest window lengths verified")
```

`last` remembers the most recent index. The left boundary never moves backward. After the update, the current window has no repeated character. Each index advances once, giving O(n) expected time. Python characters here are code points; user-perceived grapheme clusters require more text processing.

## 5. Binary search and boundary thinking

Binary search repeatedly discards a region known not to contain the desired answer. It needs sorted data or a monotonic predicate. Monotonic means once the condition becomes true along the search order, it remains true.

```python
# lab: lower_bound
def lower_bound(values, target):
    low, high = 0, len(values)
    while low < high:
        middle = low + (high-low)//2
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low

assert lower_bound([1,3,3,7], 3) == 1
assert lower_bound([1,3,3,7], 8) == 4
assert lower_bound([], 2) == 0
print("First not-less-than position verified")
```

The candidate region is half-open `[low, high)`. Everything before low is too small, and the answer cannot lie after the maintained upper boundary. Equality moves high left, finding the first matching position. If all values are too small, returning len(values) is a valid insertion position, not a valid element index.

**Exam trap:** Binary search on an unsorted list can return a plausible but wrong answer. State the precondition.

## 6. Sorting: order the cards

Insertion sort grows a sorted prefix by inserting each next item; it is simple and useful for small or nearly sorted inputs, but quadratic in the worst case. Selection sort repeatedly selects a minimum. Bubble sort repeatedly swaps adjacent out-of-order items; it is mainly pedagogical.

Merge sort sorts halves and merges them, giving O(n log n) comparison work and commonly O(n) extra array storage. Quicksort partitions around a pivot and recurses, with expected O(n log n) but quadratic worst cases for unsuitable pivot behavior. Heapsort uses a heap for O(n log n) worst-case time and in-place array implementations, but is not typically stable.

Stable sorting preserves relative order of equal keys. Counting sort uses bounded discrete keys; radix sort processes key digits using appropriate passes. Their costs depend on key range or representation, so they do not contradict comparison-sorting lower bounds. Production language sorts use engineered hybrids rather than always one textbook algorithm.

```python
# lab: merge_sort
def merge_sort(values):
    if len(values) < 2:
        return list(values)
    middle = len(values)//2
    left = merge_sort(values[:middle])
    right = merge_sort(values[middle:])
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    return result + left[i:] + right[j:]

assert merge_sort([4,1,3,1]) == [1,1,3,4]
assert merge_sort([]) == []
print("Split, sort, merge")
```

Each recursive call handles a smaller list. During merging, the result contains the smallest consumed values in order. Taking left first on ties preserves relative order under compatible key handling. Python slicing in this teaching version creates extra objects; explain actual implementation costs if asked to optimize.

## 7. Stacks, monotonic structures, and intervals

A stack matches nested brackets: push opening brackets, then require the corresponding closing bracket. It also supports DFS and undo histories. A monotonic stack keeps values ordered so elements can be discarded once they can no longer answer future questions, such as finding the next greater value.

Interval problems often begin by sorting starts. To merge intervals, extend the current interval when the next start overlaps its end; otherwise finish the current group. Define whether touching endpoints count as overlap and whether intervals are closed or half-open.

```python
# lab: merge_intervals
def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if start > end:
            raise ValueError("reversed interval")
        if not merged or start > merged[-1][1]:
            merged.append([start,end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged

assert merge_intervals([(1,3),(2,5),(7,8)]) == [[1,5],[7,8]]
assert merge_intervals([(1,2),(2,3)]) == [[1,3]]
print("Closed intervals touching at an endpoint merge")
```

Sorting dominates with O(n log n) time. The invariant is that completed output groups do not overlap and the last group covers all currently connected processed intervals. The code does not mutate the original interval pairs.

## 8. Trees, heaps, and top-k

A binary tree gives each node at most two children. A binary search tree imposes an ordering invariant; without balancing, its height can become n. Preorder visits node before children, inorder visits left-node-right, and postorder visits children before node. Level order uses a queue.

A min-heap keeps its smallest item at the root with a parent/child ordering rule. For the largest k elements, keep a min-heap of at most k: replace its smallest when a larger value arrives. This costs O(n log k) time and O(k) storage for a streaming top-k implementation.

```python
# lab: top_k
import heapq
def largest_k(values, k):
    if k < 0:
        raise ValueError("k must be nonnegative")
    if k == 0:
        return []
    heap = []
    for value in values:
        if len(heap) < k:
            heapq.heappush(heap, value)
        elif value > heap[0]:
            heapq.heapreplace(heap, value)
    return sorted(heap, reverse=True)

assert largest_k([1,9,2,8,3], 2) == [9,8]
assert largest_k([4], 0) == []
print("Largest values retained with bounded heap")
```

The heap stores the current best k candidates, with the easiest one to discard at the root. Sorting the final heap gives display order and adds O(k log k). A heap alone does not promise that iterating all entries returns sorted values.

## 9. Graphs: BFS, DFS, and dependency order

Vertices are places or tasks; edges are connections. BFS explores by edge count using a queue and finds shortest paths in unweighted graphs. DFS explores one branch deeply and is useful for reachability, traversal, and some cycle checks. Directed and undirected cycle detection require different handling.

```python
# lab: bfs_path
from collections import deque
def shortest_path(graph, start, goal):
    queue = deque([start])
    parent = {start:None}
    while queue:
        node = queue.popleft()
        if node == goal:
            path = []
            while node is not None:
                path.append(node); node = parent[node]
            return path[::-1]
        for neighbor in graph.get(node, []):
            if neighbor not in parent:
                parent[neighbor] = node
                queue.append(neighbor)
    return None

g = {"A":["B","C"], "B":["D"], "C":["D"], "D":[]}
assert shortest_path(g,"A","D") == ["A","B","D"]
assert shortest_path(g,"D","A") is None
print("Unweighted shortest route reconstructed")
```

Mark a node discovered when enqueuing so repeated edges do not enqueue it indefinitely. `parent` both records discovery and reconstructs the route. Time is O(V+E) for adjacency-list traversal, where V counts vertices and E edges.

Topological sorting orders prerequisites in a directed acyclic graph. Kahn's algorithm repeatedly removes nodes with zero incoming edges. If unprocessed nodes remain, a cycle exists. This maps directly to build systems and agent task dependencies. Strongly connected component algorithms such as Tarjan or Kosaraju identify mutually reachable groups in directed graphs; they need more than ordinary undirected connected-components logic.

## 10. Weighted routes and connectivity

Dijkstra repeatedly expands the smallest tentative distance and relaxes outgoing edges. It requires nonnegative weights for its ordinary guarantee. Bellman-Ford handles negative edges and can detect reachable negative cycles, with higher O(VE) time. Floyd-Warshall solves all-pairs shortest paths in O(V cubed) time for a dense dynamic-programming formulation.

A* orders search using cost so far plus a heuristic remaining cost. Admissibility means the heuristic does not overestimate the optimum remaining cost; graph-search details such as reopening and consistency also matter. A useful heuristic reduces search, while a poor one may behave like uninformed search or invalidate guarantees.

```python
# lab: dijkstra
import heapq
def distances_from(graph, start):
    if any(weight < 0 for edges in graph.values() for _, weight in edges):
        raise ValueError("Dijkstra requires nonnegative weights")
    distance = {start:0}
    heap = [(0,start)]
    while heap:
        cost, node = heapq.heappop(heap)
        if cost != distance[node]:
            continue
        for neighbor, weight in graph.get(node, []):
            candidate = cost + weight
            if candidate < distance.get(neighbor, float('inf')):
                distance[neighbor] = candidate
                heapq.heappush(heap, (candidate,neighbor))
    return distance

g = {"A":[("B",4),("C",1)], "C":[("B",1)], "B":[]}
assert distances_from(g,"A")["B"] == 2
print("Cheaper indirect weighted route found")
```

The heap can contain stale entries; the comparison skips them. This teaching version uses comparable string node names for heap ties. Arbitrary unorderable objects need an additional tie-breaker counter.

Union-find tracks disjoint groups using representatives. Path compression shortens lookup chains; union by rank/size balances merging. Kruskal's minimum-spanning-tree algorithm sorts edges and uses union-find to reject cycles; Prim grows a spanning tree from a frontier. A minimum spanning tree minimizes total connection cost, not source-to-everywhere route distance. Do not confuse it with Dijkstra's output.

## 11. Recursion, backtracking, and dynamic programming

Recursion solves a problem through smaller versions. A base case stops it. Backtracking tries a choice, explores consequences, and undoes the choice before trying another. Generating subsets, permutations, and constraint assignments uses this pattern; worst-case search can be exponential.

Dynamic programming reuses overlapping subproblem answers. Define the state, recurrence, base cases, evaluation order, and answer location. Memoization computes on demand; tabulation fills an ordered table. An elegant recurrence with the wrong state can still be incorrect.

```python
# lab: coin_change
def fewest_coins(coins, amount):
    if amount < 0 or any(c <= 0 for c in coins):
        raise ValueError("positive coins and nonnegative amount required")
    dp = [0] + [float('inf')]*amount
    for value in range(1, amount+1):
        for coin in coins:
            if coin <= value:
                dp[value] = min(dp[value], 1+dp[value-coin])
    return -1 if dp[amount] == float('inf') else int(dp[amount])

assert fewest_coins([1,3,4], 6) == 2
assert fewest_coins([2], 3) == -1
assert fewest_coins([2], 0) == 0
print("Optimal count found; unreachable case handled")
```

`dp[value]` means the fewest coins for exactly that value with unlimited reuse. Try each possible last coin and reuse the smaller answer. Greedy would choose 4+1+1 for amount 6, but 3+3 is better. A greedy choice needs a proof for the problem, not just a successful example.

Other recurring DP states: knapsack by item and capacity, edit distance by two prefix lengths, longest common subsequence by prefixes, and interval DP by endpoints. Complexity follows number of states times transitions per state, with memory reductions possible only when dependencies allow them.

## 12. Strings, prefixes, bits, and algorithm coverage map

Prefix sums store cumulative totals so an interval sum becomes one subtraction. For [2,3,4], prefix [0,2,5,9] gives sum of indices 1 through 2 as 9-2=7. Difference arrays efficiently represent repeated range increments before a final prefix reconstruction.

KMP string matching uses a prefix/failure structure to avoid repeatedly rechecking matched characters. Rabin-Karp compares rolling hashes and must account for collisions, often verifying candidate matches. Tries answer prefix queries by following characters. Suffix arrays/trees support richer substring queries with more complex construction and space tradeoffs.

Bit operations manipulate binary digits: AND tests shared set bits, OR combines, XOR toggles differing bits, and shifts move positions under the language's rules. A bitmask can encode a small subset. `n & (n-1)` clears the lowest set bit for positive integer n. Java fixed-width overflow/shift behavior differs from Python's arbitrary-precision integers.

| Family | Learn deeply first | Further topics introduced by name and purpose |
|---|---|---|
| Sequences | Hashing, two pointers, windows, prefix sums | Monotonic deque, sweep line |
| Search/order | Binary search, merge sort, heaps | Quickselect, external sorting, counting/radix |
| Trees | Traversals, ordering, balance idea | AVL, red-black, B-tree, segment/Fenwick trees |
| Graphs | BFS, DFS, Dijkstra, topological ordering | SCC, MST, union-find, max flow, matching |
| Optimization | Greedy proof, DP, backtracking | Branch-and-bound, approximation, randomized algorithms |
| Strings | Prefixes, trie concept, exact matching | KMP, rolling hash, suffix structures |
| ML algorithms | Objective, gradients, validation | Use the earlier AI book for model-family derivations |

This table is an honest depth map, not a claim that every named advanced method has a complete implementation here. For advanced interviews, choose the role's relevant families and work full problems on them.

## 13. All five classic creational patterns

Creational patterns organize object construction. They are useful when construction varies or has important rules.

| Pattern | Child-sized story | Concrete software example | Main caution |
|---|---|---|---|
| Factory Method | A school lets each classroom choose its workbook | A base exporter workflow delegates creation of a PDF or CSV writer to an overridable creation method | Not every helper named factory implements this pattern |
| Abstract Factory | Buy a matching chair-and-desk set | Create compatible light-theme button and dialog objects from one family factory | Too many families create unnecessary abstraction |
| Builder | Assemble a lunch with ordered options | Build a validated report request with selected sections and limits | Do not use it where a simple constructor is clearer |
| Prototype | Copy a prepared worksheet template | Clone a configured object and customize selected properties | Decide shallow versus deep copy semantics |
| Singleton | One official notice board in a defined room | One shared registry instance under an explicit lifecycle | Global mutable state harms tests and concurrency; scope matters |

Factory Method varies a creation step through a subtype or equivalent extension point. Abstract Factory creates related families. Builder separates assembly from the completed object. Prototype copies an existing object. Singleton controls instance availability. These solve distinct problems and should not be collapsed into “ways to call new.”

### Lab: Builder with an invariant

```python
# lab: builder_pattern
from dataclasses import dataclass
@dataclass(frozen=True)
class ReportRequest:
    topic: str
    limit: int

class ReportBuilder:
    def __init__(self):
        self._topic = ""
        self._limit = 3
    def topic(self, value):
        self._topic = value.strip(); return self
    def limit(self, value):
        self._limit = value; return self
    def build(self):
        if not self._topic or not 1 <= self._limit <= 10:
            raise ValueError("invalid report request")
        return ReportRequest(self._topic, self._limit)

request = ReportBuilder().topic("agents").limit(2).build()
assert request == ReportRequest("agents",2)
print(request)
```

The builder collects options, returns itself for chaining, and validates before creating the final value. Its mutable staging object is separate from the immutable request. Do not share one mutable builder across unrelated concurrent requests.

## 14. All seven classic structural patterns

Structural patterns arrange objects and interfaces.

| Pattern | Child-sized story | Working scenario | Main caution |
|---|---|---|---|
| Adapter | A plug adapter joins incompatible sockets | Convert a provider's `generate_text` API into your application's `complete` interface | Preserve error and cancellation semantics |
| Bridge | Remote-control shape and device type vary separately | Separate report abstraction from rendering backend | Requires two independent dimensions of variation |
| Composite | A folder contains files and other folders | Give leaf tasks and task groups a common cost interface | Define which leaf/group operations make sense |
| Decorator | Add a jacket without changing the child | Wrap a predictor with timing or caching while preserving its interface | Wrapper order changes behavior |
| Facade | One reception desk coordinates departments | Expose one checkout operation over inventory and billing subsystems | Avoid turning the facade into all business logic |
| Flyweight | Reuse a shared stamp design | Share immutable glyph data while positions remain external | Shared intrinsic state must not accidentally become per-user mutable state |
| Proxy | A gatekeeper stands before a resource | Add access checks or lazy loading before forwarding a call | Do not hide unexpected network or transaction cost |

Adapter changes how an existing interface is presented. Decorator adds behavior through wrapping. Proxy controls access or indirection. Facade simplifies a subsystem's surface. Similar-looking wrapper code can serve different intent, so identify the problem rather than only its syntax.

```python
# lab: adapter_decorator
class LegacyModel:
    def generate_text(self, prompt):
        return {"text": prompt.upper()}

class ModelAdapter:
    def __init__(self, legacy): self.legacy = legacy
    def complete(self, text): return self.legacy.generate_text(text)["text"]

class CountingDecorator:
    def __init__(self, wrapped): self.wrapped, self.calls = wrapped, 0
    def complete(self, text):
        self.calls += 1
        return self.wrapped.complete(text)

model = CountingDecorator(ModelAdapter(LegacyModel()))
assert model.complete("learn") == "LEARN"
assert model.calls == 1
print("Adapter translated; decorator counted")
```

The adapter extracts the provider-specific text field. The decorator preserves `complete` while adding counting. The counter is a local teaching metric, not a concurrency-safe production telemetry system. Neither wrapper makes the underlying output trustworthy.

## 15. All eleven classic behavioral patterns

Behavioral patterns organize collaboration and choices.

| Pattern | Child-sized story | Concrete scenario | Main caution |
|---|---|---|---|
| Chain of Responsibility | Pass a request along helpers until one can handle it | Validation/authentication/handler chain | Define whether processing stops or continues |
| Command | Write an instruction on a card | Queue a named operation with arguments and identity | Retrying side effects needs idempotency |
| Interpreter | Follow the grammar of a little language | Evaluate a small approved expression DSL | Do not replace a safe grammar with arbitrary eval |
| Iterator | Read one card at a time without seeing the box internals | Traverse paginated records lazily | Define mutation and resource-lifetime behavior |
| Mediator | A teacher coordinates students | Central coordinator routes interactions among components | Can become a bottleneck or oversized coordinator |
| Memento | Save a game snapshot | Restore a prior editor state without exposing its internals | External effects may not be reversible |
| Observer | A notice board informs subscribers | Notify views when a domain event occurs | Ordering, duplicate delivery, and failures matter |
| State | A traffic light behaves according to its phase | Reservation behavior changes from draft to confirmed | Prevent illegal transitions explicitly |
| Strategy | Choose a travel method | Swap ranking or pricing algorithms behind one interface | Use when behavior genuinely varies |
| Template Method | Follow a recipe with a few customizable steps | Fixed import pipeline calls overridable parse/validate hooks | Inheritance coupling can be restrictive |
| Visitor | Bring a specialist to each object kind | Add operations across a stable typed tree without editing each node's operation list | New node types can require updates to every visitor |

### Lab: Strategy and State

```python
# lab: strategy_state
def rank(items, score):
    return sorted(items, key=score, reverse=True)
assert rank(["a","bbbb","cc"], len) == ["bbbb","cc","a"]

allowed = {"draft":{"submit":"review"},
           "review":{"approve":"done", "reject":"draft"},
           "done":{}}
def transition(state, event):
    if event not in allowed[state]:
        raise ValueError("illegal transition")
    return allowed[state][event]
assert transition("review","approve") == "done"
try:
    transition("done","submit")
except ValueError:
    pass
else:
    raise AssertionError("illegal transition allowed")
print("Strategy selected behavior; state table protected transitions")
```

Passing `len` is a functional Strategy implementation: behavior is supplied independently of the sorting orchestration. The transition table demonstrates the State idea without a separate class for each state. A class-based implementation can move state-specific behavior into state objects when complexity warrants it.

### Lab: Command and Observer

```python
# lab: command_observer
from dataclasses import dataclass
@dataclass(frozen=True)
class AddPoints:
    amount: int
    def execute(self, score): return score + self.amount

events = []
subscribers = [events.append]
score = AddPoints(3).execute(2)
for subscriber in subscribers:
    subscriber({"type":"score_changed", "score":score})
assert events == [{"type":"score_changed","score":5}]
print(events)
```

The command represents an operation as an object. Subscribers receive a change event. This direct in-process broadcast does not provide durable delivery, retry, or distributed ordering. Those requirements need additional architecture, not just renaming the list an event bus.

## 16. Principles and architecture patterns beyond GoF

SOLID, DRY, KISS, and YAGNI guide tradeoffs; they are not numerical laws. A practical interpretation is to make responsibilities and invariants clear, isolate expected changes, and avoid needless indirection. Favor high cohesion and explicit dependencies. Dependency injection supplies collaborators; it does not require a framework container.

Layered architecture separates concerns by level. Hexagonal/ports-and-adapters architecture isolates domain policy from external interfaces. Clean architecture emphasizes dependency direction toward stable policy. MVC separates model/view/controller concerns; MVVM uses a view model to mediate display behavior. React components do not require every one of these labels to be forced onto the same code.

Repository abstracts persistence; Unit of Work coordinates tracked changes. CQRS separates command and read concerns. Event sourcing records events as the source of truth. Outbox coordinates local state and eventual publication. Saga coordinates distributed steps and compensation. Circuit breaker, bulkhead, retry, and timeout handle different failure/resource concerns. Cache-aside loads missing values through the application; write-through and write-behind have different consistency and failure behavior.

In AI systems, Strategy fits model or retriever selection, Adapter fits provider SDKs, Decorator fits tracing, Command fits tool proposals, State fits agent workflows, and Composite fits task hierarchies. These patterns help organize code; none proves model accuracy, safety, or effective reasoning.

## 17. Design exercises with explained answers

**A. Two model providers return incompatible objects.** Use an Adapter at the boundary and normalize results and errors. Do not spread provider-specific field access across business logic.

**B. Add timing around existing predictors.** A Decorator preserves the predictor interface and wraps the call. Decide how to report failures and whether timing includes retries.

**C. An order can ship only after payment.** Represent valid states and transitions, enforce authoritative storage constraints, and test illegal events. A State design clarifies behavior; it does not by itself solve concurrent database updates.

**D. Choose fastest shipping or cheapest shipping.** Strategy allows interchangeable scoring/selection behavior. Define tie-breaking and constraints so “cheapest” does not accidentally choose an invalid route.

**E. Add an export format to an otherwise fixed export workflow.** A Factory Method or injected factory may isolate construction. Template Method may fit stable workflow steps, but composition may be simpler if variation is not naturally hierarchical.

**F. Repeated network timeout after a mutation.** Use durable idempotency and status lookup; a retry loop alone can duplicate effects. The problem spans architecture and storage, not just one GoF pattern.

## 18. Exam routine and mastery checks

For an algorithm, explain input assumptions, invariant, steps, correctness intuition, time, space, and edge cases. For a pattern, explain the problem, participants, interactions, alternative, and cost. A pattern name without a justified problem is weak design reasoning.

Practice one 30-minute coding problem and one 15-minute design explanation. Afterwards, write the specific mistake: off-by-one, incorrect invariant, hidden mutation, unhandled empty input, wrong complexity, or missing permission boundary. Repeat a changed problem rather than memorizing the old answer.

This notebook implements representative recurring techniques and catalogs broader families. It does not claim implementations of every listed advanced method. A research algorithm exam, competitive-programming contest, Java certification, and frontend interview emphasize different material; tailor final drills to the actual assessment while preserving these foundations.


Advanced continuation: [13-patterns-workshop](13-patterns-workshop.html). The advanced workshop and accompanying projects extend the introductory scope described above.
