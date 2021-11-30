import pytest

from precise_nlp.extract.path import PathManager


@pytest.mark.parametrize(('text', 'exp'), [
    ('A) colon polyp: (see comment). B) COLON, 15 CM. COMMENT (A): more text',
     {
         'a': [' colon polyp: (see comment).'],
         'b': [' colon, 15 cm. ']
     }
     ),
    ('''A. COLON, CECAL AND ASCENDING POLYPS, POLYPECTOMY:
- Tubular adenomas.

B. COLON, TRANSVERSE POLYP, POLYPECTOMY:
- Tubular adenoma.

C. COLON, DESCENDING POLYP, POLYPECTOMY:
- Tubular adenoma.''',
     {
         'a': [' colon, cecal and ascending polyps, polypectomy:\n- tubular adenomas.'],
         'b': [' colon, transverse polyp, polypectomy:\n- tubular adenoma.'],
         'c': [' colon, descending polyp, polypectomy:\n- tubular adenoma.'],
     }
     ),
])
def test_comment(text, exp):
    actual = PathManager.parse_jars(text)[2]
    assert list(actual.keys()) == list(exp.keys())
    for letter, act_texts in actual.items():
        exp_texts = exp[letter]
        for act_text, exp_text in zip(act_texts, exp_texts):
            assert act_text.strip() == exp_text.strip()

