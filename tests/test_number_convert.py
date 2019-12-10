import pytest

from precise_nlp.extract.utils import NumberConvert


@pytest.mark.parametrize(('text', 'exp'), [
    ('two sessile polyps', 2),
    ('a pedunculated polyp was found', 1),
])
def test_contains(text, exp):
    res = NumberConvert.contains(text, followed_by=('polyp', 'polyps'),
                                 distance=2, split_on_non_word=True)
    assert res and exp == res[0]
