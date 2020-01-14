import pytest

from precise_nlp.const.enums import Location
from precise_nlp.extract.cspy.finding_builder import FindingBuilder


def test_single_polyp():
    s = 'There was one sessile polyp in the ascending colon.' \
        ' The polyp was 6mm in diameter and removed using cold biopsy.'
    fb = FindingBuilder()
    fb.extract_findings(s)
    lst = list(fb.get_findings())
    assert len(lst) == 1
    f = lst[0]
    assert f.count == 1
    assert f.locations == (Location.PROXIMAL,)
    assert f.removal
    assert f.size == 8
