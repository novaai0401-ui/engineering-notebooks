import math
import pytest
from coach_math import softmax
def test_shift_invariance_and_normalization():
    assert softmax([1000.,1001.])==pytest.approx(softmax([0.,1.]))
    assert sum(softmax([1000.,1001.]))==pytest.approx(1)
@pytest.mark.parametrize('values',[[],[math.nan],[math.inf],[-math.inf]])
def test_invalid(values):
    with pytest.raises(ValueError):softmax(values)
