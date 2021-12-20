import pytest

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.cspy.finding_patterns import apply_finding_patterns


@pytest.mark.parametrize('text, exp_count, exp_size, exp_locations', [
    ('Polyp (15 mm) in the descending colon', 1, 15, {'descending'}),
    ('Polyp (10 mm)-in the sigmoid colon. (Polypectomy)', 1, 10, {'sigmoid'}),
    ('Polyp (10 mm)-in the distal sigmoid colon. (Polypectomy)', 1, 10, {'sigmoid'}),
    ('Polyp (12 mm) in the splenic flexure. (Polypectomy)', 1, 12, {'splenic'}),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps)', 2, 4, {'ascending'}),
    ('Polyps (2 mm to 4 mm) In the rectum (polyps)', 2, 4, {'rectum'}),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps) and rectum (polyps)', 2, 4, {'ascending', 'rectum'}),
    ('One 3 mm polyp in the descending colon', 1, 3, {'descending'}),
    ('One diminutive polyp in the cecum', 1, 1, {'cecum'}),
    ('Two medium sized polyps in the cecum', 2, 5, {'cecum'}),
    ('Three moderately-sized polyps in the cecum', 3, 5, {'cecum'}),
    ('Ten large polyps in the cecum', 10, 10, {'cecum'}),
    ('One small polyp in the descending colon', 1, 1, {'descending'}),
    ('Four 3 to 5 mm polyps in the rectum', 4, 5, {'rectum'}),
    ('POLYP: Location: Descending colon. Size: 5 mm', 1, 5, {'descending'}),
    ('Transverse Colon - one 5 mm sessile polyp(s) (removed with jumbo biopsy forceps)', 1, 5, {'transverse'}),
    ('Sigmoid Colon - one 10 mm sessile polyp(s)', 1, 10, {'sigmoid'}),
    ('Rectum - two 2 mm sessile polyp(s)', 2, 2, {'rectum'}),
    ('Sigmoid Colon - two 15 mm pedunculated polyp(s)', 2, 15, {'sigmoid'}),
])
def test_finding_pattern(text, exp_count, exp_size, exp_locations):
    findings = list(apply_finding_patterns(text))
    print(findings)
    assert len(findings) == 1, 'No findings found in text'
    assert findings[0].count == exp_count
    assert findings[0].size == exp_size
    assert set(findings[0].locations) == set(exp_locations)
