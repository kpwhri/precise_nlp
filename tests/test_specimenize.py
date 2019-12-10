import pytest

from precise_nlp.extract.path import PathManager


@pytest.mark.parametrize(('text', 'output'), [
    ('A) colon polyp: (see comment). B) COLON, 15 CM. COMMENT (A): more text',
     {
         'a': [' colon polyp: (see comment).'],
         'b': [' colon, 15 cm. ']
     }
     ),
])
def test_comment(text, output):
    assert PathManager.parse_jars(text)[2] == output
