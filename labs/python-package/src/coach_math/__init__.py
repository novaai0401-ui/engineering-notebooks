"""Small typed, runtime-validated probability utility."""
import math
from collections.abc import Sequence
def softmax(values: Sequence[float]) -> list[float]:
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError('nonempty finite values required')
    largest=max(values)
    terms=[math.exp(value-largest) for value in values]
    total=sum(terms)
    return [term/total for term in terms]
