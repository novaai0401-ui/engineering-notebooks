# Study Coach Math

A minimal typed package used by Notebook 9. `coach_math.softmax` accepts a nonempty sequence of finite floats, subtracts the maximum before exponentiation, and returns normalized probabilities. Empty input, NaN and infinities are rejected.

From this directory, in the notebook Python environment, run `python -m build`, `python -m pip install .`, `python -m mypy --strict src`, and `python -m pytest -q`. The `src` layout and `py.typed` marker make installation and typing part of the exercise. The tests check shift invariance, normalization and invalid input rather than merely repeating the implementation.
