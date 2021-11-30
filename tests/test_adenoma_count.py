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
     )
])
def test_adenoma_count(text, exp):
    assert PathManager(text).get_adenoma_count().count == exp
