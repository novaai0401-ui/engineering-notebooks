# Notebook 9 — Python engineering, mathematics, and ML from scratch

Think of an ML system as a kitchen. Python is how you arrange the work, arrays are trays of ingredients, an algorithm is a recipe, and evaluation is tasting food that was not used to adjust the recipe. Good code, good mathematics and honest experiments must work together.

## 1. Packaging and typed boundaries

A notebook is good for exploration. A package gives reusable code a stable address, dependencies, tests and a version. The companion `labs/python-package` uses a `src` layout, a `pyproject.toml`, a typed public function, unit tests and a wheel build. Run `python -m build` in that folder to create an installable artifact. Type-check with `mypy --strict src` and run its tests with the package installed.

The `src` layout helps catch a common mistake: tests importing a source directory that will not actually be included in the built distribution. A type hint documents and checks a contract for static analysis; it does not automatically validate untrusted runtime JSON. Validate boundary data separately. Prefer a small protocol when you need interchangeable model providers, rather than having domain code import every provider SDK.

```python
# lab: typed_predictor_boundary
from typing import Protocol, Sequence
class Predictor(Protocol):
    def predict(self, rows: Sequence[float]) -> list[float]: ...
class DoublePredictor:
    def predict(self, rows: Sequence[float]) -> list[float]:
        return [2*x for x in rows]
def mean_prediction(model: Predictor, rows: Sequence[float]) -> float:
    if not rows:
        raise ValueError('empty data')
    predictions = model.predict(rows)
    if len(predictions) != len(rows):
        raise ValueError('one prediction required per row')
    return sum(predictions)/len(predictions)
assert mean_prediction(DoublePredictor(), [1, 2, 3]) == 4
print('Domain code depends on a prediction contract')
```

## 2. Debugging and profiling with a hypothesis

Start with the smallest reproducible input. Read the full traceback from the failing operation outward. Inspect shapes, dtypes, missing values and units before changing an optimizer. An array shaped `(n,)` can broadcast against `(n,1)` into `(n,n)`, creating a wrong loss that still runs.

```python
# lab: broadcasting_bug
import numpy as np
prediction = np.array([[1.], [2.], [3.]])
target = np.array([1., 2., 3.])
wrong = prediction-target
assert wrong.shape == (3, 3)
correct = prediction.ravel()-target
assert correct.shape == (3,) and np.all(correct == 0)
print('Shape validation catches a silent broadcasting error')
```

Use `breakpoint()` to inspect a local failing state. Use `cProfile` for Python call costs and a monotonic timer for wall time. Profile representative workloads with warmup where appropriate. A GPU call may be asynchronous, so timing its launch alone does not measure completion. First prove correctness, then identify the dominant cost; replacing readable code with a clever one-liner is not evidence of a speed improvement.

```python
# lab: profile_and_memory
import cProfile, io, pstats, tracemalloc
profiler = cProfile.Profile()
profiler.enable()
total = sum(i*i for i in range(10000))
profiler.disable()
buffer = io.StringIO()
pstats.Stats(profiler, stream=buffer).sort_stats('cumulative').print_stats(3)
assert 'function calls' in buffer.getvalue() and total > 0
tracemalloc.start()
items = [str(i) for i in range(5000)]
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
assert peak >= current > 0
print('Profile captured; Python allocation peak observed')
```

`tracemalloc` does not measure every native or GPU allocation. NumPy slices may be views retaining a large base allocation; `.copy()` owns separate storage but costs memory. Generators reduce materialization but do not magically release everything their closures reference. Close file handles with `with`, clear unnecessary references, and measure resident memory for whole-process investigation.

## 3. Floating-point arithmetic and stable transformations

A floating-point number has finite precision and range. Adding a tiny value to a huge value may lose the tiny contribution. Exponentiating large logits may overflow. Softmax is unchanged when the same constant is subtracted from every logit, so subtract the maximum before exponentiating. Log-sum-exp uses the same idea.

```python
# lab: stable_probabilities
import numpy as np
def softmax(logits):
    shifted = np.asarray(logits, dtype=float)-np.max(logits)
    exp = np.exp(shifted)
    return exp/exp.sum()
def logsumexp(values):
    values=np.asarray(values,dtype=float)
    maximum=values.max()
    return maximum+np.log(np.exp(values-maximum).sum())
p=softmax([1000,1001,1002])
assert np.isfinite(p).all() and np.isclose(p.sum(),1)
assert np.allclose(p,softmax([0,1,2]))
assert np.isfinite(logsumexp([1000,1001]))
print('Large logits produce finite normalized probabilities')
```

This routine assumes a nonempty finite input. Production utilities must define behavior for NaN, infinity and fully masked vectors. For binary logistic loss use `logaddexp(0, z) - y*z`; taking `log(sigmoid(z))` directly can underflow. Scaling features improves optimizer conditioning; fit the scaling parameters on training data only.

## 4. Statistics that explain uncertainty

The population is the collection we care about; the sample is what we observed. A sample mean estimates a population mean. Variance measures spread around the mean. Standard error describes variability of an estimator across repeated samples, not variability of individual observations. Under independent sampling, the mean's estimated standard error is sample standard deviation divided by the square root of sample size.

A confidence interval is a procedure with long-run coverage under its assumptions, not a probability that a fixed parameter moves around. A p-value is the probability, under a stated null model, of a result at least as incompatible as the observed one according to the test statistic. It is not the probability that the null hypothesis is true. Effect size and uncertainty matter more than a lone threshold.

```python
# lab: bootstrap_mean
import numpy as np
rng=np.random.default_rng(42)
sample=np.array([2.,3.,3.,4.,5.,6.,7.,8.])
resamples=rng.choice(sample,size=(3000,len(sample)),replace=True).mean(axis=1)
low,high=np.quantile(resamples,[0.025,0.975])
assert low < sample.mean() < high
print({'mean':sample.mean(),'bootstrap_interval':(round(low,2),round(high,2))})
```

Bootstrap resamples approximate repeated sampling from the empirical distribution. They do not repair selection bias or dependence. For time series use a method that preserves relevant dependence, such as suitable blocks, and assess its assumptions. For users with many sessions, split by user to avoid information leakage. Repeatedly tuning on the test set turns it into development data.

For comparing two models, evaluate the same held-out cases so differences can be paired. Stratify important categories, inspect label quality, and avoid treating correlated prompts as independent samples. An accuracy increase on mostly easy cases can coexist with worse behavior on critical rare cases.

## 5. Linear regression from scratch

We predict a number with `prediction = Xw + b`. The mean squared error averages squared mistakes. Its gradient with respect to weights is `2 Xᵀ(prediction-y)/n`; the bias gradient is twice the mean error. Move opposite these gradients by a small learning rate. Here each feature row has one number, and the true rule is `3x+2`.

```python
# lab: scratch_linear_regression
import numpy as np
X=np.arange(6,dtype=float).reshape(-1,1)/5
y=3*X[:,0]+2
w=np.zeros(1); b=0.
for _ in range(3000):
    error=X@w+b-y
    w-=0.1*(2*X.T@error/len(y))
    b-=0.1*2*error.mean()
assert np.allclose(w,[3],atol=1e-5) and abs(b-2)<1e-5
print('Recovered slope and intercept:',w.round(3),round(b,3))
```

The loss is convex for linear least squares, but convergence speed depends on conditioning and step size. A very large step can diverge. Collinear features can make coefficients non-unique or unstable. Ridge adds a squared-weight penalty; it trades some bias for stability. Prediction quality and interpretability of a coefficient are different questions, especially when features correlate.

## 6. Logistic regression from scratch

For a binary label, compute a score `z=Xw+b`, then sigmoid `1/(1+exp(-z))`. This models the probability of label one. The cross-entropy gradient with respect to the score is `p-y`, so weight updates resemble linear regression with a different prediction and loss. A threshold chooses a class; the threshold should reflect costs, not automatically be 0.5.

```python
# lab: scratch_logistic_regression
X=np.array([[-2.],[-1.],[1.],[2.]])
y=np.array([0.,0.,1.,1.]);w=np.zeros(1);b=0.
for _ in range(1000):
    z=X@w+b
    p=1/(1+np.exp(-np.clip(z,-40,40)))
    w-=0.1*(X.T@(p-y)/len(y))
    b-=0.1*(p-y).mean()
loss=np.mean(np.logaddexp(0,X@w+b)-y*(X@w+b))
assert np.array_equal((X@w+b>0).astype(int),y.astype(int))
assert loss<0.02
print('Binary labels learned; stable cross-entropy:',round(float(loss),4))
```

On perfectly separable data, unregularized coefficients can keep increasing even when every classification is correct. That is why accuracy alone does not tell you whether optimization is well behaved. Calibration asks whether predicted probabilities correspond to observed frequencies; ranking performance and calibration are different properties.

## 7. Neighbors, clustering, and principal components

K-nearest neighbors stores training examples and votes among nearby ones. “Nearby” depends on the distance metric and scaling. K-means alternates assigning each point to its nearest center and replacing each center with its assigned mean. Its objective is within-cluster squared Euclidean distance; it does not discover every possible cluster shape. PCA finds orthogonal directions explaining maximal centered variance; high variance is not automatically high predictive value.

```python
# lab: scratch_knn_kmeans_pca
from collections import Counter
def knn(train,labels,point,k):
    order=np.argsort(np.sum((train-point)**2,axis=1),kind='stable')[:k]
    counts=Counter(labels[i] for i in order)
    return sorted(counts,key=lambda label:(-counts[label],label))[0]
points=np.array([[0.,0.],[0.,1.],[8.,8.],[9.,8.]])
assert knn(points,[0,0,1,1],np.array([0.,0.2]),3)==0
centers=points[[0,2]].copy()
for _ in range(20):
    labels=((points[:,None,:]-centers[None,:,:])**2).sum(axis=2).argmin(axis=1)
    updated=np.array([points[labels==k].mean(axis=0) if np.any(labels==k) else centers[k] for k in range(2)])
    if np.allclose(updated,centers):break
    centers=updated
assert labels.tolist()==[0,0,1,1]
centered=points-points.mean(axis=0)
_,singular,directions=np.linalg.svd(centered,full_matrices=False)
projected=centered@directions[:1].T
assert projected.shape==(4,1) and singular[0]>=singular[1]
print('Neighbors, alternating cluster updates, and PCA projection verified')
```

The K-means empty-cluster policy here keeps the previous center; other policies reinitialize it. Try several initializations and compare the objective. For PCA, center using the training mean and reuse that mean at inference. Standardize features when their units would otherwise dominate the variance objective. Singular vectors may flip sign without changing the subspace.

## 8. A recursive decision tree from scratch

A tree asks a question, sends examples left or right, and repeats. Classification impurity measures how mixed the labels are. Gini impurity is `1 - sum(class_probability²)`: zero means all labels agree. Choose a split minimizing weighted child impurity, then stop when labels agree, depth is exhausted, or no useful split exists.

```python
# lab: scratch_decision_tree
def gini(labels):
    if not len(labels): return 0.
    counts=np.unique(labels,return_counts=True)[1]/len(labels)
    return 1-float(np.sum(counts**2))
def fit_tree(X,y,depth=3):
    values,counts=np.unique(y,return_counts=True)
    leaf=int(values[counts.argmax()])
    if depth==0 or len(values)==1:return leaf
    best=None
    for column in range(X.shape[1]):
        unique=np.unique(X[:,column])
        for threshold in (unique[:-1]+unique[1:])/2:
            left=X[:,column]<=threshold
            score=(left.sum()*gini(y[left])+(~left).sum()*gini(y[~left]))/len(y)
            if best is None or score<best[0]:best=(score,column,float(threshold),left)
    if best is None:return leaf
    _,column,threshold,left=best
    return (column,threshold,fit_tree(X[left],y[left],depth-1),fit_tree(X[~left],y[~left],depth-1))
def tree_predict(tree,row):
    if isinstance(tree,int):return tree
    column,threshold,left,right=tree
    return tree_predict(left if row[column]<=threshold else right,row)
X=np.array([[0.,0.],[0.,1.],[1.,0.],[1.,1.]])
y=np.array([0,1,1,0])
tree=fit_tree(X,y)
assert [tree_predict(tree,row) for row in X]==y.tolist()
print('Recursive splits represent XOR; one linear boundary cannot')
```

This tiny tree intentionally permits an initial split with no immediate impurity improvement, allowing XOR to be represented. Production tree algorithms often use minimum-gain thresholds and additional regularization. Trees overfit with unrestricted depth. Bagging reduces variance by averaging independently perturbed trees; boosting adds learners to correct an objective's current errors. These are different ensemble mechanisms.

## 9. Backpropagation is the chain rule applied repeatedly

For a two-layer network, `H=tanh(XW1+b1)` and `Y=HW2+b2`. Backward propagation multiplies each upstream derivative by the local derivative. Tanh's derivative is `1-H²`. A finite-difference check perturbs one parameter slightly and compares the observed loss slope to the analytic gradient. This catches transposes, missing averages and wrong activation derivatives before a long training run.

```python
# lab: manual_backprop_gradient_check
rng=np.random.default_rng(3)
X=rng.normal(size=(4,2));target=rng.normal(size=(4,1))
W1=rng.normal(size=(2,3));W2=rng.normal(size=(3,1))
def loss_and_gradient(A):
    H=np.tanh(X@A);error=H@W2-target
    loss=float(np.mean(error**2))
    dY=2*error/len(X)
    dA=X.T@((dY@W2.T)*(1-H**2))
    return loss,dA
loss,gradient=loss_and_gradient(W1)
eps=1e-6;plus=W1.copy();minus=W1.copy()
plus[0,1]+=eps;minus[0,1]-=eps
numeric=(loss_and_gradient(plus)[0]-loss_and_gradient(minus)[0])/(2*eps)
assert np.isclose(numeric,gradient[0,1],rtol=1e-5,atol=1e-6)
print('Analytic backprop matches a numerical loss derivative')
```

For outputs with multiple columns, account for the loss's exact averaging convention. Finite differences are expensive and sensitive to step size; use small double-precision examples. Automatic differentiation computes gradients, but it cannot tell you whether your loss expresses the intended problem.

## 10. Design exercise with answer key

**Task, 20 points:** Package a classifier behind a typed predictor, reject empty or malformed data, split before preprocessing, record a baseline, measure memory and latency, and explain one failure.

Award 3 points for an installable package and tests; 3 for boundary validation and types; 4 for leakage-safe evaluation; 4 for a correct from-scratch algorithm and gradient or invariant check; 3 for measured performance with workload details; 3 for a specific limitation. Do not award “production-ready” points merely because training accuracy is 100%.

**Debugging answer:** If loss has shape `(n,n)` and should have shape `(n,)`, fix shapes at the boundary before tuning learning rate. **Statistics answer:** A narrow confidence interval around a biased estimate does not make it correct. **Design answer:** Keep training, prediction, storage and transport separate enough to test independently, but do not create an interface for every single function without a reason.
