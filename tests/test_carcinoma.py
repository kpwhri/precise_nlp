import pytest

from precise_nlp.extract.path import JarManager


@pytest.mark.parametrize('text, exp', [
    ('NEGATIVE FOR HIGH-GRADE DYSPLASIA OR INVASIVE CARCINOMA', 0),
    ('INVASIVE CARCINOMA', 1),
])
def test_get_carcinomas(text, exp):
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_count() == exp
