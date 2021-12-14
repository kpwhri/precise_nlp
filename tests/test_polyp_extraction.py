import pytest

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.cspy.cspy import FindingVersion


@pytest.mark.parametrize('text, exp', [
    (
            '''Impressions: Polyp: (4mm) in the descending colon. (Polypectomy).
            Polyp (10 mm)-in the sigmoid colon. (Polypectomy).
            Polyp (14 mm) in the sigmoid colon. (Polypectomy).''',
            3
    )
])
def test_polyp_count(text, exp):
    cm = CspyManager(text, version=FindingVersion.PRECISE)
    findings = list(cm.get_findings())
    assert len(findings) == exp
