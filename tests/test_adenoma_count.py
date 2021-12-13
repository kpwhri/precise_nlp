import pytest

from precise_nlp.extract.path import PathManager


@pytest.mark.parametrize(('text', 'exp'), [
    ('''
A. COLON, CECAL AND ASCENDING POLYPS, POLYPECTOMY:
- Tubular adenomas.

B. COLON, TRANSVERSE POLYP, POLYPECTOMY:
- Tubular adenoma.

C. COLON, DESCENDING POLYP, POLYPECTOMY:
- Tubular adenoma.''', 4
     ),
    ('A. COLON, TRANSVERSE POLYPS, POLYPECTOMY:\n- Tubular adenoma, 1 fragment.', 1),
    ('A. COLON, TRANSVERSE POLYPS, POLYPECTOMY:\n- Tubular adenoma, | fragment.', 1),
    ('POLYPS: adenoma', 1),
    ('A. COLON, TRANSVERSE POLYPS, POLYPECTOMY:\n- Tubular adenoma, 1 of 5 fragments.', 1),
    ('sessile serrated adenoma', 0),
    ('sessile serrated lesion', 0),
    ('sessile serrated polyp', 0),
])
def test_adenoma_count(text, exp):
    assert PathManager(text).get_adenoma_count().count == exp
