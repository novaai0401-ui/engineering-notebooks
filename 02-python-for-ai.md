# Notebook 2 — Python for AI, ML, and Generative AI

Learn only the Python foundations and engineering habits that support data, models, retrieval, agents, and services. This is an original self-contained lesson sequence, not a catalog of every Python feature. Read without installing anything; running labs requires the recorded Python packages. Start from the first cell and run in order.

## 1. A program is a careful recipe

A variable is a label attached to an object. A function is a reusable recipe. A list stores an ordered collection. A dictionary associates keys with values. A loop repeats work. An exception signals that a requested operation could not complete normally.

Python indentation marks blocks. `=` assigns; `==` compares. Strings hold text. Integers represent whole numbers, floats approximate many real numbers, and Booleans represent true or false. `None` represents an absent value by convention; it differs from zero, an empty string, and false.

```python
# lab: values_and_functions
def total_price(count, unit_price, delivery=0):
    if count < 0:
        raise ValueError("count cannot be negative")
    return count * unit_price + delivery

assert total_price(3, 10, delivery=5) == 35
prices = {"pencil":5, "book":20}
cart = ["pencil", "book", "pencil"]
total = sum(prices[item] for item in cart)
assert total == 30
print(total)
```

The function receives two required values and one default. The conditional rejects an invalid count. The return statement produces the answer. The dictionary connects each name to a price. The generator expression looks up one price per item, and `sum` adds them. In a money-handling system use integer minor units or deliberate decimal arithmetic rather than casual float rounding.

**Exercise:** What happens when a cart item is absent from the dictionary? **Answer:** Direct lookup raises KeyError. Decide whether missing means invalid, unavailable, or eligible for a default; do not silently treat every missing price as zero.

## 2. Mutability, copying, and common traps

Two labels can point to the same list. Changing that list is visible through both names. A shallow copy creates a new outer container while nested mutable objects can remain shared. A deep copy recursively copies more structure, but copying everything is not always the correct design.

```python
# lab: mutation
original = [[1], [2]]
shallow = original.copy()
shallow[0].append(9)
assert original[0] == [1, 9]

def append_label(label, labels=None):
    result = [] if labels is None else list(labels)
    result.append(label)
    return result

assert append_label("a") == ["a"]
assert append_label("b") == ["b"]
print("Each call receives its intended list")
```

A mutable default such as `labels=[]` is created when the function is defined, not freshly on every call. The `None` pattern avoids surprising shared defaults. A tuple is an immutable sequence but can contain mutable objects. Sets keep distinct hashable members and are useful for membership tests; they do not replace ordered records when order matters.

**Interview check:** Is Python pass-by-value or pass-by-reference? **Answer:** A useful precise account is that arguments bind local names to passed objects. Mutating a shared object can be visible; rebinding a local name does not rebind the caller's variable.

## 3. Iteration, comprehensions, and generators

`enumerate` supplies index and value. `zip` pairs corresponding values but normally stops at the shortest input; use deliberate length checking when silent truncation is wrong. A comprehension builds a collection. A generator yields items on demand, avoiding a full intermediate list.

```python
# lab: batches
from itertools import islice

def batches(items, size):
    if size <= 0:
        raise ValueError("size must be positive")
    iterator = iter(items)
    while True:
        group = list(islice(iterator, size))
        if not group:
            return
        yield group

assert list(batches(range(7), 3)) == [[0,1,2],[3,4,5],[6]]
print("Batches preserve the last partial group")
```

`iter` gives a stream of items. `islice` reads at most the next size items. An empty group signals completion. `yield` returns one group while preserving the function's continuation. This is useful for documents, embedding requests, and minibatches. A generator can be exhausted; do not expect it to restart automatically.

## 4. Functions, closures, decorators, and types

Functions are objects: you can pass a scoring function to a sorter. A closure remembers bindings from an enclosing scope. A decorator accepts a callable or class and returns a replacement or wrapped object; it is how many tool registries register functions.

```python
# lab: function_registry
registry = {}
def register(function):
    registry[function.__name__] = function
    return function

@register
def square(value: float) -> float:
    """Multiply a value by itself."""
    return value * value

assert registry["square"](4) == 16
print(sorted(registry))
```

`@register` applies the registration function after defining `square`. The annotation describes expected types; ordinary Python does not enforce all annotations at runtime. Use explicit checks or a validation library at untrusted boundaries. Wrapping decorators should preserve metadata when needed, commonly with `functools.wraps`.

Use small pure functions for calculations. A pure function does not secretly read changing global state or perform external effects. File access, network calls, and model loading belong in visible boundaries so tests can substitute controlled implementations.

## 5. Classes, dataclasses, and composition

A class groups state and behavior. An instance is one created object. A dataclass generates common record methods from declared fields. Prefer combining objects through explicit interfaces over building deep inheritance trees only to reuse a few lines.

```python
# lab: composition
from dataclasses import dataclass
from typing import Protocol

class Scorer(Protocol):
    def score(self, text: str) -> int: ...

@dataclass(frozen=True)
class LengthScorer:
    def score(self, text: str) -> int:
        return len(text.split())

def choose_longest(texts: list[str], scorer: Scorer) -> str:
    if not texts:
        raise ValueError("at least one text required")
    return max(texts, key=scorer.score)

assert choose_longest(["hello", "hello learner"], LengthScorer()) == "hello learner"
print("A scorer was supplied as a dependency")
```

The protocol states the capability the caller needs. The concrete object supplies it. `frozen=True` prevents ordinary field reassignment, not every possible deep mutation. Injecting dependencies makes it easy to replace a real model with a deterministic fake during tests.

## 6. Files, JSON, exceptions, and cleanup

JSON exchanges basic structured values; it does not safely encode arbitrary executable Python objects. `with` manages cleanup even when an exception occurs. Catch specific expected failures, preserve useful context, and do not silently turn every failure into a success-shaped empty result.

```python
# lab: json_roundtrip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as folder:
    target = Path(folder) / "record.json"
    target.write_text(json.dumps({"id":"doc-1", "text":"Hello"}), encoding="utf-8")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["id"] == "doc-1"
print("JSON read back; temporary directory cleaned up")
```

Use explicit encodings. Validate record shape after loading. Treat pickle and other executable serialization formats as trusted-input-only unless you have a deliberately controlled security model. Do not `eval` user text. Path validation matters when a user chooses filenames; joining a path alone does not prevent traversal outside an allowed directory.

## 7. NumPy: a fast table of numbers

An ndarray has a shape and a data type. Think of shape as the box dimensions. `(3,2)` means three rows with two values each. Vectorization sends work to optimized array routines rather than a Python loop per element. Broadcasting aligns compatible dimensions; it is convenient but can silently create the wrong shape if you do not check.

```python
# lab: numpy_shapes
import numpy as np
X = np.array([[1.,2.],[3.,4.],[5.,6.]])
w = np.array([2.,-1.])
prediction = X @ w
assert prediction.shape == (3,)
assert np.allclose(prediction, [0.,2.,4.])
centered = X - X.mean(axis=0)
assert np.allclose(centered.mean(axis=0), [0.,0.])
print(prediction.tolist())
```

`@` performs matrix multiplication. `axis=0` averages down rows, producing one mean per column. Broadcasting subtracts those two means from each row. `*` instead performs elementwise multiplication under broadcasting. Shape `(n,)` is not interchangeable with `(n,1)` in all expressions: mixing them can create an unintended `(n,n)` result.

Views may share underlying storage; `.copy()` requests independent data. Check dtype before accumulating large counts or using low precision. Numerical stability matters: subtract the maximum score before softmax and avoid taking log of an unintended zero.

**Exercise:** Multiply shape `(4,3)` by `(3,2)` using `@`. **Answer:** `(4,2)`. Explain the shared dimension before doing arithmetic.

## 8. pandas: records, missingness, and joins

A DataFrame is a labeled table. It is useful for ingestion and analysis, while tensors or arrays feed many models. Missing is not always zero. A join combines records using keys, and duplicate keys can multiply rows unexpectedly.

```python
# lab: pandas_join
import pandas as pd
users = pd.DataFrame({"user_id":[1,2], "group":["A","B"]})
events = pd.DataFrame({"user_id":[1,1,2], "value":[2,3,4]})
joined = events.merge(users, on="user_id", validate="many_to_one")
totals = joined.groupby("group")["value"].sum().to_dict()
assert totals == {"A":5,"B":4}
print(totals)
```

The merge attaches a group to each event. `validate` asserts the expected key relationship. `groupby` gathers rows by group; selecting `value` and summing produces group totals. Before training, inspect duplicate identifiers, label availability dates, missing values, and unexpected types. Train-serving consistency begins in these mundane checks.

## 9. scikit-learn: prevent leakage with pipelines

Imagine practicing an exam with its answer distribution already revealed. Preprocessing on the whole dataset can create a milder form of that problem. Fit preprocessing only on training examples, including inside each cross-validation fold. Pipelines tie transformations and predictors into one fitting procedure. [Official leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).

```python
# lab: sklearn_pipeline
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

X = np.array([[i, i % 3] for i in range(-20, 21)], dtype=float)
y = np.array([int(i >= 0) for i in range(-20, 21)])
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=7, stratify=y)
model = make_pipeline(StandardScaler(), LogisticRegression(random_state=7))
model.fit(X_train, y_train)
probabilities = model.predict_proba(X_test)[:,1]
assert probabilities.shape == y_test.shape
assert np.all((probabilities >= 0) & (probabilities <= 1))
print("Held-out predictions:", len(probabilities))
```

This toy has an intentionally simple label rule; its score would not prove real-world usefulness. `fit` learns both scaler and classifier using training only. `predict_proba` returns columns per class; here column one corresponds to class 1. Real evaluation additionally needs the correct time/group split, metrics, threshold choice, uncertainty, and an untouched final test.

## 10. PyTorch: tensors and gradients

A tensor resembles an array with support for devices and automatic differentiation. A computation graph records differentiable operations. `backward()` computes gradients; an optimizer changes parameters. Those are different responsibilities.

```python
# lab: torch_gradient
import torch
w = torch.tensor(7.0, requires_grad=True)
prediction = w * 2.0
loss = 0.5 * (prediction - 20.0) ** 2
loss.backward()
assert abs(w.grad.item() + 12.0) < 1e-6
with torch.no_grad():
    w -= 0.1 * w.grad
    w.grad.zero_()
assert abs(w.item() - 8.2) < 1e-5
print(round(w.item(), 2))
```

The first tensor is trainable. Loss is half the squared price error. Backpropagation produces -12. `no_grad` prevents the parameter update from building an unnecessary derivative graph. Gradients accumulate by default, so clear them for the next intended independent update. `.item()` extracts a scalar for reporting; doing this inside a differentiable calculation disconnects that value from autograd.

In a normal loop: load a batch, clear gradients, predict, compute loss, backpropagate, and step the optimizer. `model.train()` changes behavior of modules such as dropout; `model.eval()` changes that behavior for evaluation. Neither alone disables autograd. Use an appropriate no-gradient/inference context for evaluation. Seed experiments and report nondeterminism limits rather than assuming every device produces identical runs.

## 11. Text, tokens, embeddings, and retrieval in Python

A token is a unit from a tokenizer, not necessarily a whole word. An embedding is a numerical representation. A similarity score measures closeness under a representation and metric; it is not automatically a probability of correctness.

### Lab: retrieval mechanics with transparent word vectors

```python
# lab: toy_retrieval
from collections import Counter
import math
def bag(text):
    return Counter(text.lower().split())

def cosine_counts(a, b):
    dot = sum(value*b.get(word,0) for word,value in a.items())
    norm_a = math.sqrt(sum(v*v for v in a.values()))
    norm_b = math.sqrt(sum(v*v for v in b.values()))
    return dot/(norm_a*norm_b) if norm_a and norm_b else 0.0

documents = {"A":"plants need water", "B":"planets orbit stars"}
query = bag("plants water")
ranking = sorted(documents, key=lambda k: cosine_counts(query, bag(documents[k])), reverse=True)
assert ranking[0] == "A"
print(ranking)
```

This is lexical bag-of-words retrieval, not a pretrained semantic embedding model. Counters store term frequencies. The numerator combines shared coordinates, and norms normalize vector length. Empty input has an explicit score convention. A full RAG system adds parsing, chunk metadata, authorization, reranking, context selection, generation, citation verification, and evaluation.

## 12. Async, threads, processes, and batching

Async is useful when work waits on sockets, files, or other supported asynchronous operations. A coroutine must yield for others to proceed on the same event loop. A blocking call inside it can stall the loop. Threads can help I/O and native routines; ordinary CPU-heavy Python code often needs processes or native kernels for useful parallelism on conventional GIL-enabled builds. Python builds and extensions vary, so benchmark the actual runtime.

```python
# lab: async_limit
import asyncio
async def double_later(value, limit):
    async with limit:
        await asyncio.sleep(0)
        return value*2

async def run_batch():
    limit = asyncio.Semaphore(2)
    return await asyncio.gather(*(double_later(v, limit) for v in range(4)))

values = await run_batch()
assert values == [0,2,4,6]
print(values)
```

Notebook code uses top-level `await`; a normal standalone script can call `asyncio.run(run_batch())`. Do not call `asyncio.run` inside an already-running notebook event loop. Bound concurrency and timeouts, distinguish retryable errors, and maintain cancellation semantics. More concurrent requests can cause rate limiting rather than more throughput.

## 13. Architecture and design principles for ML code

Separate data ingestion, transformation, training, evaluation, model artifacts, and serving. Keep the feature transformation and model version together. A result should identify its data snapshot and configuration so you can reproduce or diagnose it.

```text
raw records -> validated records -> split -> fitted pipeline -> artifact
                                       |                         |
                                  held-out evaluation       serving adapter
```

Use dependency injection for repositories, model clients, clocks, and random generators. Define a narrow predictor interface instead of importing provider SDKs throughout the business logic. Configuration belongs in explicit validated settings; secrets belong in a controlled environment or secret store rather than source code or notebooks.

Design pure transformations that accept data and return data. Keep effects in adapters. Prefer composition to inheritance when swapping a retriever or scorer. Use Strategy for interchangeable scoring, Adapter for provider APIs, Factory for configuration-driven construction, and Repository for persistent access. A pattern is useful only when it simplifies a real variation or boundary.

## 14. Testing, environments, packaging, and debugging

A unit test checks a small function. An integration test checks connected components. A contract test checks request/response shape. An end-to-end test checks a user journey. ML additionally needs data-quality checks, leakage checks, slice metrics, and regression evaluation. Test the property you care about, not merely that a method was called.

Use virtual environments to isolate dependencies, pin compatible versions for repeatable labs, and keep an environment report with results. A lockfile describes a resolved environment more exactly than a loose list of package names. A notebook can hide execution order; restart the kernel and run all cells to reveal missing dependencies between cells.

Debug from the first failing assumption: input shape, dtype, missingness, target definition, gradient connection, device placement, then optimization. Profile before optimizing. Vectorization, batching, caching, and better algorithms have different effects; a faster incorrect pipeline is still incorrect.

## 15. Capstone and exam practice

Build a document classifier with a clean input schema, leakage-safe split, baseline, fitted preprocessing, evaluation report, saved artifact, and prediction wrapper. Add a deterministic fake predictor for interface tests. Explain how deployment receives exactly the same transformations and what happens to unknown categories or empty text.

**1. Why zero gradients?** Because autograd accumulates them unless cleared; accumulation should be intentional.

**2. Why a pipeline?** It keeps preprocessing fitting within the correct training boundary and makes inference consistent.

**3. Why not `.item()` midway through a loss?** It converts to a Python scalar and loses the gradient connection for that path.

**4. List comprehension versus generator?** The first materializes results; the second yields lazily, with different lifetime and reuse behavior.

**5. Why use a context manager?** It scopes resource acquisition and cleanup, including exceptional exits.

**6. Does a type hint validate hostile JSON?** No. Perform runtime validation.

**7. Why is a shared notebook global risky?** Later cells can accidentally depend on earlier hidden state. Test fresh execution.

**8. When can a data join leak the future?** When historical rows receive attributes updated after their prediction time. Use point-in-time semantics.

Detailed coverage: Python values, collections, mutation, functions, decorators, protocols, files, JSON, generators, NumPy, pandas, scikit-learn, PyTorch, retrieval, async, testing, and architecture. Introductions only: distributed training internals, GPU kernel programming, advanced numerical analysis, metaclasses, and packaging native extensions. Those are specialized topics, not prerequisites for every AI engineering role. The [official Python tutorial](https://docs.python.org/3/tutorial/) supports the language baseline; no external reading is needed for these labs.


Advanced continuation: [09-python-ai-depth](09-python-ai-depth.html). The advanced workshop and accompanying projects extend the introductory scope described above.
