import pytest

from precise_nlp.extract.maybe_counter import MaybeCounter


def test_create_maybe():
    c = MaybeCounter(1)
    assert c.count == 1
    assert not c.at_least
    assert not c.greater_than
    c = MaybeCounter(2, at_least=True)
    assert c.count == 2
    assert c.at_least
    assert not c.greater_than
    c = MaybeCounter(0, greater_than=True)
    assert c.count == 0
    assert not c.at_least
    assert c.greater_than
    with pytest.raises(ValueError):
        MaybeCounter(2, at_least=True, greater_than=True)


@pytest.mark.parametrize('c1, c2, exp', [
    (MaybeCounter(1), MaybeCounter(2), MaybeCounter(3)),
    (MaybeCounter(2, at_least=True),
     MaybeCounter(2),
     MaybeCounter(4, at_least=True)
     ),
    (MaybeCounter(2),
     MaybeCounter(2, greater_than=True),
     MaybeCounter(5, at_least=True)
     ),
    (MaybeCounter(2, greater_than=True),
     MaybeCounter(3, at_least=True),
     MaybeCounter(6, at_least=True)
     ),
    (MaybeCounter(0, at_least=True),
     MaybeCounter(1, at_least=True),
     MaybeCounter(1, at_least=True)
     ),
    (MaybeCounter(2, greater_than=True),
     MaybeCounter(3, greater_than=True),
     MaybeCounter(7, at_least=True)
     ),

])
def test_add(c1, c2, exp):
    c3 = c1 + c2
    assert c3.count == exp.count
    assert c3.greater_than == exp.greater_than
    assert c3.at_least == exp.at_least


@pytest.mark.parametrize('c, i, gt', [
    (MaybeCounter(1), 1, -1),
    (MaybeCounter(2), 1, 1),
    (MaybeCounter(2), 3, -1),
    (MaybeCounter(2, greater_than=True), 3, 0),
    (MaybeCounter(3, greater_than=True), 3, 1),
    (MaybeCounter(0, greater_than=True), 3, -1),
    (MaybeCounter(0, greater_than=True), 2, 0),
    (MaybeCounter(2, at_least=True), 2, 0),
    (MaybeCounter(3, at_least=True), 2, 1),
    (MaybeCounter(0, at_least=True), 2, -1),
    (MaybeCounter(0, at_least=True), 1, 0),
])
def test_gt_limit2(c, i, gt):
    MaybeCounter.GREATER_THAN_LIMIT = 2
    assert c.gt(i) == gt


@pytest.mark.parametrize('c, i, gt', [
    (MaybeCounter(1), 1, -1),
    (MaybeCounter(2), 1, 1),
    (MaybeCounter(2), 3, -1),
    (MaybeCounter(2, greater_than=True), 3, 0),
    (MaybeCounter(3, greater_than=True), 3, 1),
    (MaybeCounter(0, greater_than=True), 3, -1),
    (MaybeCounter(0, greater_than=True), 2, -1),
    (MaybeCounter(2, at_least=True), 2, 0),
    (MaybeCounter(3, at_least=True), 2, 1),
    (MaybeCounter(0, at_least=True), 2, -1),
    (MaybeCounter(1, at_least=True), 2, -1),
])
def test_gt(c, i, gt):
    MaybeCounter.GREATER_THAN_LIMIT = 1  # default value
    assert c.gt(i) == gt


@pytest.mark.parametrize('c, i, eq', [
    (MaybeCounter(1), 1, 1),
    (MaybeCounter(2), 1, -1),
    (MaybeCounter(2), 3, -1),
    (MaybeCounter(2, greater_than=True), 3, 0),
    (MaybeCounter(3, greater_than=True), 3, -1),
    (MaybeCounter(0, greater_than=True), 3, -1),
    (MaybeCounter(0, greater_than=True), 2, 0),
    (MaybeCounter(2, at_least=True), 2, 0),
    (MaybeCounter(3, at_least=True), 2, -1),
    (MaybeCounter(0, at_least=True), 2, -1),
    (MaybeCounter(1, at_least=True), 2, 0),
])
def test_eq_limit2(c, i, eq):
    MaybeCounter.GREATER_THAN_LIMIT = 2
    assert c.eq(i) == eq


@pytest.mark.parametrize('c, i, eq', [
    (MaybeCounter(1), 1, 1),
    (MaybeCounter(2), 1, -1),
    (MaybeCounter(2), 3, -1),
    (MaybeCounter(2, greater_than=True), 3, 0),
    (MaybeCounter(3, greater_than=True), 3, -1),
    (MaybeCounter(0, greater_than=True), 3, -1),
    (MaybeCounter(0, greater_than=True), 2, -1),
    (MaybeCounter(2, at_least=True), 2, 0),
    (MaybeCounter(3, at_least=True), 2, -1),
    (MaybeCounter(0, at_least=True), 2, -1),
    (MaybeCounter(1, at_least=True), 2, -1),
])
def test_gt(c, i, eq):
    MaybeCounter.GREATER_THAN_LIMIT = 1  # default value
    assert c.eq(i) == eq

