import pytest

from precise_nlp.extract.algorithm import has_large_adenoma_precise
from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.path import PathManager


@pytest.mark.parametrize('path_text, cspy_text, exp', [
    (
        '''COLON, DESCENDING AND SIGMOID POLYPS, POLYPECTOMY:
        - Two tubulovillous adenomas; see Comment.
        - One tubular adenoma; see Comment.''',
        '''Impressions: Polyp: (4mm) in the descending colon. (Polypectomy).
        Polyp (10 mm)-in the sigmoid colon. (Polypectomy).
        Polyp. (14 mm) in the sigmoid colon. (Polypectomy).''',
        1
    ),
])
def test_has_large_adenoma_precise(path_text, cspy_text, exp):
    """

    :param path_text:
    :param cspy_text:
    :param exp: 0=None, 1=yes, 9=maybe
    :return:
    """
    pm = PathManager(path_text)
    cm = CspyManager(cspy_text)
    assert has_large_adenoma_precise(pm, cm) == exp
