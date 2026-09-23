# 20 — Deeper algorithms and mathematics, one small step at a time

## 1. How to learn a difficult algorithm

First say what problem it solves. Then draw a tiny example. State what remains true after each step: the invariant. Only then write the code. Test an empty case, a smallest valid case, an ordinary case and an adversarial case. Finally explain time and space cost, including the data structure assumptions.

This workshop extends the earlier sorting, searching, trees, graphs, tries, dynamic programming and union-find lessons. It covers selected specialist families; there are infinitely many variants and new research results, so “every algorithm ever” is not a finite syllabus.

## 2. Fenwick tree: boxes holding groups of sweets

You have a row of boxes. You repeatedly add sweets to one box and ask how many sweets are in the first k boxes. A plain array updates quickly but sums slowly. A Fenwick tree stores carefully chosen partial sums. Index i stores a block whose length is its lowest set binary bit, `i & -i`. A query removes that bit to jump to the preceding disjoint block. An update adds that bit to reach all containing blocks.

At index 6, binary 110, the lowest bit has value 2, so that node covers boxes 5 and 6. A prefix query at 6 uses the block at 6, then the block at 4. The blocks are disjoint and together cover 1 through 6. Each jump changes a bit, so query and update take O(log n); storage is O(n). This sum version needs invertible subtraction for range queries.

```python
# lab: fenwick_workshop
class Fenwick:
    def __init__(self,n):self.n=n;self.tree=[0]*(n+1)
    def add(self,i,delta):
        if not 0<=i<self.n:raise IndexError(i)
        i+=1
        while i<=self.n:self.tree[i]+=delta;i+=i&-i
    def prefix(self,end):
        if not 0<=end<=self.n:raise IndexError(end)
        total=0
        while end:total+=self.tree[end];end-=end&-end
        return total
    def range_sum(self,left,right):return self.prefix(right)-self.prefix(left)
f=Fenwick(6)
for i,x in enumerate([2,1,4,3,5,2]):f.add(i,x)
assert f.range_sum(1,4)==8
f.add(2,6);assert f.prefix(3)==13
print('Range [1,4) initially 8; point updates and prefix queries take logarithmic time.')
```

## 3. Segment tree: a tournament of summaries

A tournament combines pairs, then pairs of pairs, until one root summarizes everything. A segment tree works the same way. Each internal node stores a combination of its children. For sums, the identity is zero and the combination is addition. For minimum, the identity is positive infinity. The operation must be associative; subtraction does not work as a simple summary because grouping changes the result.

A range query selects O(log n) boundary nodes at each side, totaling O(log n) nodes in the standard iterative implementation. Point update is O(log n); construction and storage are O(n). Lazy propagation extends it to range updates by postponing work, but the deferred operation must compose correctly with the stored summary. Do not add a lazy flag without deriving those rules.

```python
# lab: segment_tree_workshop
class SegTree:
    def __init__(self,values):
        self.n=len(values);self.t=[0]*self.n+list(values)
        for i in range(self.n-1,0,-1):self.t[i]=self.t[2*i]+self.t[2*i+1]
    def set(self,i,value):
        if not 0<=i<self.n:raise IndexError(i)
        i+=self.n;self.t[i]=value
        while i>1:i//=2;self.t[i]=self.t[2*i]+self.t[2*i+1]
    def sum(self,left,right):
        if not 0<=left<=right<=self.n:raise IndexError('range')
        left+=self.n;right+=self.n;answer=0
        while left<right:
            if left&1:answer+=self.t[left];left+=1
            if right&1:right-=1;answer+=self.t[right]
            left//=2;right//=2
        return answer
s=SegTree([2,1,4,3,5]);assert s.sum(1,4)==8
s.set(2,10);assert s.sum(1,4)==14
assert SegTree([]).sum(0,0)==0
print('Segment tree preserves sum summaries after a point replacement.')
```

## 4. KMP: do not forget what you already matched

Searching for “ababac” in a long string can repeatedly compare the same characters. Knuth–Morris–Pratt stores a prefix table. For each pattern prefix, the table tells us the longest proper prefix that is also a suffix. After a mismatch, that suffix is already known to match; resume from its length instead of restarting blindly.

The text pointer never goes backwards. The pattern pointer may fall back, but its total forward progress bounds those fallbacks. Preprocessing is O(m), search O(n), and auxiliary space O(m). Empty-pattern behavior is a contract choice; here it matches every boundary.

```python
# lab: kmp_workshop
def kmp(text,pattern):
    if not pattern:return list(range(len(text)+1))
    pi=[0]*len(pattern);j=0
    for i in range(1,len(pattern)):
        while j and pattern[i]!=pattern[j]:j=pi[j-1]
        if pattern[i]==pattern[j]:j+=1
        pi[i]=j
    found=[];j=0
    for i,c in enumerate(text):
        while j and c!=pattern[j]:j=pi[j-1]
        if c==pattern[j]:j+=1
        if j==len(pattern):found.append(i-j+1);j=pi[j-1]
    return found
assert kmp('aaaaa','aaa')==[0,1,2]
assert kmp('abababac','ababac')==[2]
assert kmp('hi','')==[0,1,2]
print('Overlapping matches retained without restarting the text scan.')
```

## 5. Strongly connected components: groups that can all visit each other

In a directed graph, a strongly connected component is a maximal set in which every vertex can reach every other. Kosaraju's algorithm does a depth-first search to record finishing order, reverses all edges, then explores in reverse finishing order. Each second-pass tree is one component. Collapsing components creates a directed acyclic graph, useful for dependency analysis.

Both passes visit each vertex and edge a constant number of times: O(V+E) time and O(V+E) storage. The recursive teaching implementation below can exceed Python's recursion depth on a very long path; production code should use an explicit stack for large untrusted graphs.

```python
# lab: scc_workshop
def components(graph):
    vertices=set(graph)
    for edges in graph.values():vertices.update(edges)
    reverse={v:[] for v in vertices}
    for u,edges in graph.items():
        for v in edges:reverse[v].append(u)
    seen=set();order=[]
    def visit(u):
        if u in seen:return
        seen.add(u)
        for v in graph.get(u,[]):visit(v)
        order.append(u)
    for u in vertices:visit(u)
    seen=set();result=[]
    def collect(u,group):
        if u in seen:return
        seen.add(u);group.add(u)
        for v in reverse[u]:collect(v,group)
    for u in reversed(order):
        if u not in seen:
            group=set();collect(u,group);result.append(group)
    return result
assert {frozenset(x) for x in components({0:[1],1:[0,2],2:[3],3:[2]})}=={frozenset([0,1]),frozenset([2,3])}
print('Four vertices collapse into two strongly connected components.')
```

## 6. Maximum flow: pipes with limited capacity

Flow enters at a source and leaves at a sink. Every intermediate node conserves flow, and each edge has a capacity. A residual graph records both unused forward capacity and the ability to undo earlier flow through a reverse edge. Reverse edges are essential: an early choice may need correction.

Edmonds–Karp repeatedly finds a shortest residual path using BFS and augments by its smallest capacity. The general adjacency-list bound is O(VE²). The small dense implementation below scans all possible neighbors, so each BFS is O(V²), giving a looser O(V³E) bound from the O(VE) augmentation bound. When no path remains, the reachable residual vertices define a cut whose capacity equals the flow, proving optimality by the max-flow/min-cut theorem.

```python
# lab: maxflow_workshop
from collections import deque
def maxflow(capacity,source,sink):
    n=len(capacity)
    if source==sink:raise ValueError('distinct endpoints required')
    residual=[row[:] for row in capacity];total=0
    while True:
        parent=[-1]*n;parent[source]=source;q=deque([source])
        while q and parent[sink]<0:
            u=q.popleft()
            for v,c in enumerate(residual[u]):
                if c>0 and parent[v]<0:parent[v]=u;q.append(v)
        if parent[sink]<0:return total
        amount=float('inf');v=sink
        while v!=source:u=parent[v];amount=min(amount,residual[u][v]);v=u
        v=sink
        while v!=source:
            u=parent[v];residual[u][v]-=amount;residual[v][u]+=amount;v=u
        total+=amount
assert maxflow([[0,3,2,0],[0,0,1,2],[0,0,0,3],[0,0,0,0]],0,3)==5
print('Maximum flow is 5, matching the total capacity leaving the source.')
```

## 7. A-star: a map plus a sensible guess

Dijkstra chooses the smallest known distance from the start, g. A-star chooses g+h, adding an estimate of distance still needed. If h never overestimates, it is admissible. If h(u) ≤ cost(u,v)+h(v) for each edge, it is consistent. Consistency lets a standard closed-set implementation finalize nodes safely. With an admissible but inconsistent heuristic, reopening may be necessary.

For a four-neighbor grid with unit steps, Manhattan distance is consistent. For diagonal movement, that heuristic may overestimate unless adjusted to the movement costs. A zero heuristic reduces A-star to Dijkstra. A good heuristic can reduce explored nodes dramatically, but worst-case search can still be large.

## 8. Gradient descent from the shape of a bowl

Let prediction be wx and loss be L=(wx-y)²/2. The chain rule gives dL/dw=(wx-y)x: the outer square contributes the prediction error, and the inner linear expression contributes x. With x=2, y=6 and w=1, the prediction is 2, error is -4 and gradient is -8. A learning rate of 0.1 changes w to 1.8. Its prediction 3.6 is closer to 6.

The gradient points uphill; subtracting it moves downhill for a sufficiently small step. A huge learning rate can jump past the valley and diverge. Feature scaling changes the shape of the valley and can make optimization easier. A low training loss alone does not establish generalization.

```python
# lab: gradient_check_workshop
def loss(w):return (w*2-6)**2/2
w=1.0;gradient=(w*2-6)*2;eps=1e-6
numeric=(loss(w+eps)-loss(w-eps))/(2*eps)
assert abs(numeric-gradient)<1e-6
assert loss(w-.1*gradient)<loss(w)
print({'analytic_gradient':gradient,'finite_difference':round(numeric,6)})
```

## 9. Softmax and cross-entropy simplify together

For probability p_i=exp(z_i)/sum_j exp(z_j), the derivative is dp_i/dz_j=p_i(δ_ij-p_j). The diagonal is p_i(1-p_i); an off-diagonal entry is -p_i p_j. Raising one logit takes probability mass from the others.

For one-hot target y and cross-entropy L=-sum_i y_i log p_i, combining these derivatives gives dL/dz_i=p_i-y_i. This is why a complicated-looking output layer has a simple gradient. Compute log-softmax with a log-sum-exp formulation rather than taking the logarithm of a rounded probability that might become zero.

```python
# lab: cross_entropy_gradient
import numpy as np
z=np.array([2.,1.,0.]);target=1
def ce(v):
    shifted=v-v.max();return -shifted[target]+np.log(np.exp(shifted).sum())
p=np.exp(z-z.max());p/=p.sum();g=p.copy();g[target]-=1
numeric=[]
for i in range(3):
    step=np.zeros(3);step[i]=1e-6;numeric.append((ce(z+step)-ce(z-step))/2e-6)
assert np.allclose(g,numeric,atol=1e-7)
print('Cross-entropy gradient:',np.round(g,4).tolist())
```

## 10. Attention with two library cards

A query is what you seek, keys describe available cards, and values carry their content. Dot products measure query-key alignment. Divide scores by sqrt(d_k), apply a mask if future positions are forbidden, then softmax across keys. The output is a weighted sum of values.

If weights are [0.75,0.25] and values are [4,0] and [0,8], the output is [3,2]. Attention does not simply choose one card; it mixes them. Standard full self-attention forms an n-by-n score matrix, which explains its quadratic sequence-length cost. Cached autoregressive decoding reuses prior keys and values; cache memory still grows with sequence length and model dimensions.

```python
# lab: attention_workshop
import numpy as np
q=np.array([[1.,0.],[0.,1.]])
k=q.copy();v=np.array([[4.,0.],[0.,8.]])
scores=q@k.T/np.sqrt(2);scores[np.triu_indices(2,1)]=-np.inf
weights=np.exp(scores-np.max(scores,axis=1,keepdims=True));weights/=weights.sum(axis=1,keepdims=True)
output=weights@v
assert np.allclose(output[0],[4,0]);assert np.allclose(weights.sum(axis=1),1)
print('Causal attention output:',np.round(output,3).tolist())
```

## 11. Least squares without a fragile inverse

Ordinary least squares minimizes ||Xw-y||². Setting its gradient to zero gives XᵀXw=Xᵀy. That derivation is useful; explicitly computing inverse(XᵀX) is often a poor numerical implementation because forming XᵀX squares the condition number. QR or SVD-based least-squares solvers are preferable. Rank deficiency means multiple parameter vectors may explain the same observations; it is a property of the data, not something a bigger learning rate fixes.

```python
# lab: least_squares_workshop
import numpy as np
X=np.array([[1.,0.],[1.,1.],[1.,2.],[1.,3.]])
y=np.array([1.,3.,5.,7.])
q,r=np.linalg.qr(X,mode='reduced');w=np.linalg.solve(r,q.T@y)
assert np.allclose(w,[1,2]);assert np.linalg.norm(X@w-y)<1e-10
print('QR recovers intercept 1 and slope 2 without forming an explicit inverse.')
```

## 12. Statistics: uncertainty is part of the answer

For independent Bernoulli outcomes, the maximum-likelihood success estimate is successes/n. With a Beta(a,b) prior, the posterior is Beta(a+successes,b+failures), whose mean is (a+successes)/(a+b+n). A uniform Beta(1,1) prior with three successes and one failure gives posterior mean 4/6, whereas the maximum-likelihood estimate is 3/4. The prior smooths a small sample; it is an assumption you must disclose.

Bootstrap resamples observations with replacement to approximate sampling variability. It is not a cure for biased data or dependent observations. For time series, naive independent resampling destroys time structure; use a suitable block procedure or model. Data leakage from future information can make any confidence interval look reassuring around the wrong experiment.

Bias-variance decomposition under squared loss separates squared systematic error, estimator variability and irreducible noise under its assumptions. Increasing model flexibility can reduce bias while increasing variance; regularization, more representative data and appropriate validation address different parts of that tradeoff.

## 13. Specialist interview map

For graph interviews, extend to Bellman–Ford for negative edges and reachable negative cycles, Floyd–Warshall for all pairs on small dense graphs, minimum spanning trees via Kruskal or Prim, bipartite matching and topological dynamic programming. For strings, compare tries, rolling hashes, KMP and suffix structures. For optimization, distinguish convex from nonconvex problems, first-order from second-order methods, and constrained from unconstrained objectives.

For ML interviews, explain PCA as a maximum-variance orthogonal projection and SVD as a matrix factorization; EM as alternating posterior inference and parameter optimization; calibration as agreement between predicted probabilities and observed frequencies; causal identification as requiring assumptions beyond correlation. Learn assumptions and failure examples before memorizing formulas.

Timed task: choose between Fenwick and segment tree for point additions plus range sums. A good answer chooses Fenwick for simplicity and space constants, notes that segment trees generalize to more associative summaries, defines inclusive/exclusive indexing and tests negative updates. A weak answer lists both without explaining the operation contract.
