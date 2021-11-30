import pytest

from precise_nlp.extract.path import JarManager


def test_dysplasia_negation():
    text = 'negative for high grade dysplasia'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.has_dysplasia() is False


@pytest.mark.parametrize('text, exp', [
    ('negative for high grade dysplasia', 0),
    ('high grade dysplasia', 1),
    ('', 99),
    ('no evidence of highgrade dysplasia', 0),
    ('evidence of highgrade dysplasia', 1),
    ('low grade dysplasia', 0),
    ('A. lots of highgrade dysplasia; B. negative for highgrade dysplasia', 1),
])
def test_get_any_dysplasia(text, exp):
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_any_dysplasia() == exp
