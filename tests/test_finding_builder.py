import pytest

from precise_nlp.extract.cspy.finding_builder import FindingBuilder


def test_single_polyp():
    s = 'There was one sessile polyp in the ascending colon.' \
        ' The polyp was 6mm in diameter and removed using cold biopsy.'
    fb = FindingBuilder()
    fb.fsm(s)
    lst = list(fb.get_findings())
    assert len(lst) == 1
    f = lst[0]
    assert f.count == 1
    assert f.locations == ('ascending',)
    assert f.removal
    assert f.size == 6


def test_two_benign_polyps():
    s = 'Two benign sessile polyps were found'
    fb = FindingBuilder()
    fb.fsm(s)
    lst = list(fb.get_findings())
    assert len(lst) == 1
    f = lst[0]
    assert f.count == 2
    assert f.locations == ()
    assert not f.removal
    assert f.size == 0


def test_multiple_locations():
    s = 'Removed 3 polyps from ascending, descending, and cecum'
    fb = FindingBuilder()
    fb.fsm(s)
    lst = list(fb.get_findings())
    assert len(lst) == 3
    for f in lst:
        assert f.count == 1
    assert not {loc for f in lst for loc in f.locations} - {'ascending', 'descending', 'cecum'}
