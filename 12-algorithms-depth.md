# Notebook 12 — Trees, graphs, backtracking and dynamic programming

An algorithm interview is not a memory contest alone. You must turn a problem into a representation, explain why each step is safe, and test the boundary cases. This notebook extends the basic algorithms in Notebook 6. Every implementation below has an executable check; the explanations give the reasoning that a test alone cannot prove.

## 1. A correctness proof in four small steps

State the precondition: what is true before the algorithm starts? State an invariant: what remains true after every loop iteration? Show progress: what gets closer to finishing? State the postcondition: what is true when it stops? For recursion, identify a smaller subproblem and a base case. Testing finds counterexamples; a proof argues about all allowed inputs.

For binary search, the invariant can be “every index below `lo` contains a value below the target, and every index at or above `hi` contains a value at least the target.” Each comparison shrinks `[lo,hi)`. At termination the interval is empty and `lo` is the insertion boundary. Without sorted input, that proof fails even if a few examples pass.

Complexity describes how resource use grows with input size. Include the call stack, output storage, and representation costs. Expected hash-table performance differs from a worst-case guarantee. An `O(n)` algorithm with a huge allocation can lose to a simpler method on small inputs; asymptotics and measurements answer different questions.

## 2. Binary trees and search-tree invariants

A binary tree allows up to two children per node. A binary search tree additionally orders keys: every key in the left subtree is smaller and every key in the right subtree is larger under our no-duplicates convention. Checking only immediate children is insufficient. Carry lower and upper bounds down the entire path.

```python
# lab: tree_bounds_and_traversal
from dataclasses import dataclass
@dataclass
class Node:
    value:int
    left:object=None
    right:object=None
def valid_bst(node,low=float('-inf'),high=float('inf')):
    return node is None or (low<node.value<high and valid_bst(node.left,low,node.value) and valid_bst(node.right,node.value,high))
def inorder(root):
    result=[];stack=[];node=root
    while stack or node:
        while node:stack.append(node);node=node.left
        node=stack.pop();result.append(node.value);node=node.right
    return result
tree=Node(5,Node(2),Node(8,Node(6),Node(9)))
assert valid_bst(tree) and inorder(tree)==[2,5,6,8,9]
assert not valid_bst(Node(5,Node(2,None,Node(7))))
assert inorder(None)==[]
print('Ancestor bounds catch a violation that local child checks miss')
```

Both procedures take `O(n)` time. The explicit traversal stack uses `O(h)` space for height `h`; recursive validation also uses `O(h)` call depth. An unbalanced tree may have `h=n` and exceed Python's recursion limit. Balanced search trees maintain logarithmic height through rotations and balancing rules; a plain BST does not guarantee that.

## 3. Topological order and cycle detection

A directed acyclic graph represents prerequisites. Kahn's algorithm counts incoming edges, starts with nodes having none, and removes their outgoing edges. A node enters the ready queue only after all its prerequisites have been removed. If fewer than all nodes are output, a directed cycle prevented progress.

```python
# lab: topological_sort
from collections import deque
def topological(graph):
    nodes=set(graph)|{v for neighbors in graph.values() for v in neighbors}
    indegree={node:0 for node in nodes}
    for neighbors in graph.values():
        for v in neighbors:indegree[v]+=1
    ready=deque(sorted(node for node in nodes if indegree[node]==0));order=[]
    while ready:
        node=ready.popleft();order.append(node)
        for neighbor in graph.get(node,[]):
            indegree[neighbor]-=1
            if indegree[neighbor]==0:ready.append(neighbor)
    if len(order)!=len(nodes):raise ValueError('cycle')
    return order
graph={'python':['agents'],'agents':['project'],'java':['project'],'project':[]}
order=topological(graph);position={v:i for i,v in enumerate(order)}
assert all(position[u]<position[v] for u,neighbors in graph.items() for v in neighbors)
try:topological({'a':['b'],'b':['a']})
except ValueError:pass
else:raise AssertionError('cycle missed')
print('Prerequisites precede dependents; cycles are rejected')
```

Ignoring the initial sorting used for deterministic output, the algorithm is `O(V+E)` time and `O(V)` auxiliary storage. Sorting ready nodes initially adds up to `O(V log V)` here. Multiple valid orders may exist. Topological ordering is not shortest-path search, and an undirected cycle requires a different interpretation.

## 4. Union-find and minimum spanning trees

Union-find tracks disjoint groups. `find` returns a representative; `union` merges two groups. Path compression shortens future searches and union by size prevents avoidable tall trees. Its amortized cost is nearly constant, conventionally expressed using the inverse Ackermann function, for the standard sequence of operations.

```python
# lab: union_find_kruskal
class UnionFind:
    def __init__(self,n):self.parent=list(range(n));self.size=[1]*n
    def find(self,x):
        while self.parent[x]!=x:
            self.parent[x]=self.parent[self.parent[x]];x=self.parent[x]
        return x
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a==b:return False
        if self.size[a]<self.size[b]:a,b=b,a
        self.parent[b]=a;self.size[a]+=self.size[b];return True
def kruskal(n,edges):
    groups=UnionFind(n);chosen=[]
    for weight,a,b in sorted(edges):
        if groups.union(a,b):chosen.append((weight,a,b))
    if n and len(chosen)!=n-1:raise ValueError('disconnected graph')
    return chosen
selected=kruskal(4,[(1,0,1),(2,1,2),(8,0,2),(3,2,3),(9,0,3)])
assert sum(w for w,_,_ in selected)==6
assert len(selected)==3
print('Kruskal chooses the lightest safe edges without closing a cycle')
```

The cut property justifies choosing a minimum-weight edge crossing a cut between components. Sorting dominates at `O(E log E)`. A spanning tree connects every vertex with minimum total edge weight; it does not minimize each source-to-destination route. The implementation assumes valid vertex indices and an undirected graph encoded as weighted edges.

## 5. Tries for prefix queries

A trie stores one character per edge. Words sharing a prefix share the same path. A terminal marker distinguishes “a word ends here” from “this is merely a prefix.” Search and insert take `O(L)` dictionary steps for word length `L`; space depends on the stored characters and node overhead.

```python
# lab: trie_prefix
class Trie:
    END=object()
    def __init__(self):self.root={}
    def insert(self,word):
        node=self.root
        for char in word:node=node.setdefault(char,{})
        node[self.END]=True
    def walk(self,prefix):
        node=self.root
        for char in prefix:
            if char not in node:return None
            node=node[char]
        return node
    def contains(self,word):
        node=self.walk(word)
        return node is not None and self.END in node
trie=Trie()
for word in ['agent','agency','graph','']:trie.insert(word)
assert trie.walk('age') is not None and not trie.contains('age')
assert trie.contains('agent') and trie.contains('') and not trie.contains('agents')
print('Word termination is distinct from prefix existence')
```

For only exact membership, a hash set is often simpler and smaller. For autocomplete, collect descendants under the prefix but bound results and define ordering. Unicode normalization, case folding and locale rules are product decisions; blindly lowercasing does not solve every language's matching rules.

## 6. Backtracking: choose, explore, undo

Backtracking explores a decision tree while abandoning impossible partial choices. N-queens places one queen per row. A placement is safe if its column and two diagonal identifiers have not been used. When returning from a branch, undo exactly the state added for that choice.

```python
# lab: n_queens_backtracking
def queens(n):
    solutions=[];columns=set();down=set();up=set();path=[]
    def visit(row):
        if row==n:solutions.append(tuple(path));return
        for col in range(n):
            if col in columns or row-col in down or row+col in up:continue
            columns.add(col);down.add(row-col);up.add(row+col);path.append(col)
            visit(row+1)
            path.pop();columns.remove(col);down.remove(row-col);up.remove(row+col)
    visit(0);return solutions
assert len(queens(4))==2 and queens(1)==[(0,)] and queens(2)==[]
for solution in queens(4):
    assert len(set(solution))==4
    assert len({r-c for r,c in enumerate(solution)})==4
print('Pruning finds the two valid four-queen arrangements')
```

The search is exponential; a useful loose bound is factorial-style column permutations with polynomial overhead. Output storage can dominate. Returning `path` itself instead of a copy would make all saved solutions refer to later mutations. This is a frequent interview bug worth explaining before writing code.

## 7. Dynamic programming: state, recurrence, order

Dynamic programming stores answers to overlapping subproblems. For longest common subsequence, `dp[i][j]` is the best length using the first `i` characters of one string and first `j` of the other. Matching final characters add one to `dp[i-1][j-1]`. Otherwise take the better of skipping either final character. Fill smaller prefixes first.

```python
# lab: lcs_dynamic_programming
def lcs(a,b):
    dp=[[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            dp[i][j]=dp[i-1][j-1]+1 if a[i-1]==b[j-1] else max(dp[i-1][j],dp[i][j-1])
    result=[];i,j=len(a),len(b)
    while i and j:
        if a[i-1]==b[j-1]:result.append(a[i-1]);i-=1;j-=1
        elif dp[i-1][j]>=dp[i][j-1]:i-=1
        else:j-=1
    return ''.join(reversed(result))
assert lcs('abcde','ace')=='ace' and lcs('','abc')==''
assert len(lcs('ABCBDAB','BDCABA'))==4
print('Prefix recurrence computes and reconstructs a common subsequence')
```

Time and space are `O(mn)`. If only the length is needed, two rows reduce space to `O(min(m,n))`; reconstructing a sequence then needs additional technique or stored decisions. A subsequence can skip characters; a substring must be contiguous. Confusing the two produces a different recurrence.

## 8. Knapsack and the direction of iteration

For 0/1 knapsack, each item may be used once. `dp[c]` is the best value using processed items within capacity `c`. Iterate capacities downward so an item cannot reuse its own update in the same pass. Upward iteration would describe an unbounded-use variant.

```python
# lab: zero_one_knapsack
def knapsack(weights,values,capacity):
    dp=[0]*(capacity+1)
    for weight,value in zip(weights,values):
        if weight<=0:raise ValueError('positive weights required')
        for c in range(capacity,weight-1,-1):dp[c]=max(dp[c],dp[c-weight]+value)
    return dp[capacity]
assert knapsack([2,3,4],[4,5,7],5)==9
assert knapsack([2],[3],4)==3 # not 6: the item cannot be reused
assert knapsack([],[],5)==0
print('Backward capacity iteration preserves the one-use invariant')
```

This is `O(nC)` time and `O(C)` space, where C is numeric capacity. It is pseudo-polynomial because capacity may be exponentially large relative to the number of bits needed to encode it. A greedy value-to-weight ratio solves the fractional version, not arbitrary 0/1 knapsack.

## 9. Negative edges and shortest paths

Dijkstra's greedy finalization relies on nonnegative edge weights. Bellman–Ford repeatedly relaxes every edge. After k passes, distances are correct for shortest paths using at most k edges. A shortest simple path uses at most V-1 edges; another improvement afterwards indicates a reachable negative cycle.

```python
# lab: bellman_ford
def bellman_ford(n,edges,source):
    dist=[float('inf')]*n;dist[source]=0
    for _ in range(n-1):
        changed=False
        for a,b,w in edges:
            if dist[a]+w<dist[b]:dist[b]=dist[a]+w;changed=True
        if not changed:break
    if any(dist[a]+w<dist[b] for a,b,w in edges):raise ValueError('reachable negative cycle')
    return dist
assert bellman_ford(3,[(0,1,4),(0,2,5),(1,2,-2)],0)==[0,4,2]
try:bellman_ford(2,[(0,1,1),(1,0,-2)],0)
except ValueError:pass
else:raise AssertionError('negative cycle missed')
print('Negative edges work; a reachable negative cycle is rejected')
```

Worst-case time is `O(VE)`, space `O(V)` excluding input. An unreachable negative cycle does not affect distances from this source and is not detected by this source-based check. For all-pairs shortest paths, consider repeated suitable single-source algorithms or Floyd–Warshall, depending on density and constraints.

## 10. Timed rounds with alternatives and scoring

**Round A, 20 minutes:** Find duplicate values. Start with pairwise comparison `O(n²)`, then a hash set with expected `O(n)` time and `O(n)` space, then sorting with `O(n log n)` time if mutation or a copy is acceptable. Award 2 points each for assumptions, working code, complexity, edge cases and tradeoffs.

**Round B, 30 minutes:** Determine whether prerequisites are schedulable. Give Kahn's algorithm and a DFS color alternative. In DFS, gray means on the current recursion path, black means completed. An edge to gray detects a directed cycle; an edge to black does not. Award 3 points for modeling, 3 for correct cycle handling, 2 for complexity and 2 for empty/disconnected cases.

**Round C, 40 minutes:** Solve 0/1 knapsack. Explain brute-force include/exclude recursion, memoization by `(item,capacity)`, and bottom-up optimization. Award 4 points for recurrence, 4 for one-use correctness, 4 for boundary cases, 4 for pseudo-polynomial complexity, and 4 for explaining why the greedy ratio fails.

**Round D, debugging:** A tree validator accepts a left grandchild greater than the root. The missing invariant is the ancestor bound. A DP returns twice an item's value with only one item available. The likely bug is upward capacity iteration. A path algorithm produces nonsense with a negative cycle. The problem has no finite minimum for affected reachable destinations; changing a heap implementation cannot fix the mathematical issue.

Further specialist topics include balanced-tree rotations, segment/Fenwick trees, strongly connected components, max flow, string matching, suffix structures, randomized algorithms and approximation. This notebook supplies core implementations and proof habits, not a claim that the finite list exhausts algorithm research.
