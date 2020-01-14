import collections

import pytest

from precise_nlp.extract.cspy.cspy import CspyManager
from precise_nlp.extract.cspy.single_finding import SingleFinding


@pytest.mark.parametrize(('sections', 'expected_count'), [
    (('A sessile polyp was found at 55 cm proximal to the anus.',
      'The polyp was 7 mm in size.',
      'The polyp was removed with a hot snare.',
      'Resection and retrieval were complete'), 1)
])
def test_merge_findings(sections, expected_count):
    findings = collections.defaultdict(list)
    prev_locations = None
    label = None
    for s in sections:
        prev_locations = CspyManager._parse_section(findings, label, prev_locations, s)
    assert sum(f.count for f in findings[label]) == expected_count


def test_parse_finding_count():
    sentence = 'Two benign sessile polyps were found'
    f = SingleFinding.parse_finding(sentence)
    assert f.count == 2


def test_parse_finding_location():
    sentence = 'polyps found in rectum'
    f = SingleFinding.parse_finding(sentence)
    assert f.locations == ('rectum',)
