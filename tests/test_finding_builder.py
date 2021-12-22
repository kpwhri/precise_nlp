import pytest

from precise_nlp.extract.cspy.finding_builder import FindingBuilder
from precise_nlp.extract.cspy.naive_finding import NaiveFinding


@pytest.fixture
def fb():
    return FindingBuilder()


def test_single_polyp(fb):
    s = 'There was one sessile polyp in the ascending colon.' \
        ' The polyp was 6mm in diameter and removed using cold biopsy.'
    fb.fsm(s)
    lst = list(fb.get_findings())
    assert len(lst) == 1
    f = lst[0]
    assert f.count == 1
    assert f.locations == ('ascending',)
    assert f.removal
    assert f.size == 6


def test_two_benign_polyps(fb):
    s = 'Two benign sessile polyps were found'
    fb.fsm(s)
    lst = list(fb.get_findings())
    assert len(lst) == 1
    f = lst[0]
    assert f.count == 2
    assert f.locations == ()
    assert not f.removal
    assert f.size == 0


def test_multiple_locations(fb):
    s = 'Removed 3 polyps from ascending, descending, and cecum'
    fb.fsm(s)
    lst = [f for finding in fb.get_findings() for f in finding.split()]
    assert len(lst) == 3
    for f in lst:
        assert f.count == 1
    assert {loc.location[0] for f in lst for loc in f.locations} == {'ascending', 'descending', 'cecum'}


@pytest.mark.parametrize(('sections', 'expected_count'), [
    (('A sessile polyp was found at 55 cm proximal to the anus.',
      'The polyp was 7 mm in size.',
      'The polyp was removed with a hot snare.',
      'Resection and retrieval were complete'), 1)
])
def test_merge_findings(fb, sections, expected_count):
    for s in sections:
        fb.fsm(s)
    findings = fb.get_merged_findings()
    assert len(findings) == 1
    f = findings[0]
    assert f.count == 1
    assert f.size == 7
    assert f.removal
    assert f.locations == ('sigmoid',)


def test_merge_split_findings(fb):
    sections = (
        'Removed 7mm, 3mm, and 2mm polyps from transverse, ascending, descending.',
    )
    for s in sections:
        fb.fsm(s)
    findings = list(fb.split_findings2(*fb.get_merged_findings()))
    assert len(findings) == 3
    exp_sizes = (7, 3, 2)
    exp_locations = ('transverse', 'ascending', 'descending')
    for finding, exp_size, exp_loc in zip(findings, exp_sizes, exp_locations):
        assert len(finding) == 1
        assert finding.size == exp_size
        assert finding.location == exp_loc
        assert finding.removal


@pytest.mark.parametrize(('text', 'size', 'locations'), [
    ('Polyp (15 mm) in the descending colon at 50 cm', 15, ('sigmoid',)),  # 'at 50 cm' caught before 'descending'
    ('Polyp (5 mm) In the distal sigmoid colon', 5, ('sigmoid', 'distal')),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps) and rectum (polyps)', 4, ('ascending', 'rectum')),
    ('Polyp (10 mm)-in the sigmoid colon. (Polypectomy)', 10, ('sigmoid',)),
    ('Polyp (10 mm) in the sigmoid colon. (Polypectomy)', 10, ('sigmoid',)),
])
def test_finding_builder(fb, text, size, locations):
    finding = fb.fsm(text)
    assert finding.size == size
    assert set(ll for loc in finding.locations for ll in loc.location) == set(locations)


@pytest.mark.parametrize(('text', 'size', 'locations'), [
    ('Polyp (15 mm) in the descending colon at 50 cm', 15, ('descending', 'sigmoid')),
    ('Polyp (5 mm) In the distal sigmoid colon', 5, ('sigmoid', 'distal')),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps) and rectum (polyps)', 4, ('ascending', 'rectum')),
])
def test_extract_wag_polyps(text, size, locations):
    finding = NaiveFinding.parse_finding(text)
    assert finding.size == size
    assert set(finding.locations) == set(locations)
