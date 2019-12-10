import collections

import pytest

from precise_nlp.extract.cspy import CspyManager


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
