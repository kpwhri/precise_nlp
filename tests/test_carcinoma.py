import pytest

from precise_nlp.extract.path import JarManager


@pytest.mark.parametrize('text, exp', [
    ('NEGATIVE FOR HIGH-GRADE DYSPLASIA OR INVASIVE CARCINOMA', 0),
    ('INVASIVE CARCINOMA', 1),
    ('neurofibroma', 0),  # TODO: should this be included?
    ('negative for high-grade dysplasia or invasive carcinoma', 0),
    ('negative for high grade dysplasia or invasive carcinoma', 0),
    ('no high grade dysplasia or invasive carcinoma', 0),
    ('no glandular dysplasia or carcinoma identified', 0),
    ('NO INTESTINAL METAPLASIA, GLANDULAR DYSPLASIA OR CARCINOMA IDENTIFIED', 0),
])
def test_get_carcinomas(text, exp):
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_count() == exp


@pytest.mark.parametrize('text, exp', [
    ('NEGATIVE FOR HIGH-GRADE DYSPLASIA OR INVASIVE CARCINOMA', 0),
    ('negative for high-grade dysplasia or invasive carcinoma', 0),
    ('negative for high grade dysplasia or invasive carcinoma', 0),
    ('no high grade dysplasia or invasive carcinoma', 0),
    ('no glandular dysplasia or carcinoma identified', 0),
    ('NO INTESTINAL METAPLASIA, GLANDULAR DYSPLASIA OR CARCINOMA IDENTIFIED', 0),
    ('likely carcinoma', 1),
])
def test_get_carcinomas_maybe(text, exp):
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == exp
