import pytest

from precise_nlp.extract.polarity_counter import PolarityCounter


@pytest.mark.parametrize('kwarg_list, exp_positive, exp_negative, exp_unknown', [
    ([{'positive': 0, 'negative': 0}], 0, 0, True),
    ([{'positive': 0, 'negative': 0}, {'positive': 0, 'negative': 0}], 0, 0, True),
    ([{'positive': 1, 'negative': 0}, {'positive': 2, 'negative': 0}], 3, 0, False),
    ([{'positive': 0, 'negative': 2}, {'positive': 2, 'negative': 5}], 2, 7, False),
    ([{'positive': 0, 'negative': 2}, {'positive': 2, 'negative': 5}, {'positive': 0, 'negative': 0}], 2, 7, False),
])
def test_polarity_counter(kwarg_list, exp_positive, exp_negative, exp_unknown):
    ctr = sum([PolarityCounter(**kwargs) for kwargs in kwarg_list[1:]], start=PolarityCounter(**kwarg_list[0]))
    assert ctr.positive == exp_positive
    assert ctr.negative == exp_negative
    assert ctr.unknown == exp_unknown
