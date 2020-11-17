import pytest

from precise_nlp.const.enums import AssertionStatus
from precise_nlp.extract.path import JarManager


def test_carcinoma_count():
    text = 'adenosquamous carcinoma'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 1


def test_carcinoma_maybe_count():
    text = 'suspicious for adenosquamous carcinoma'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 1
    assert jm.get_carcinoma_count() == 0


def test_carcinoma_value():
    text = 'suspicious for adenosquamous carcinoma'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    jar = jm.get_current_jar()
    assert jar.carcinoma_list[0][0] == 'adenosquamous carcinoma'
    assert jar.carcinoma_list[0][1] == AssertionStatus.POSSIBLE


def test_carcinoma_count_rectal_melanoma():
    text = 'rectal, adenoma, melanoma'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 1


def test_carcinoma_count_colonic_melanoma():
    text = 'descending, adenoma, melanoma'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 0


def test_carcinoma_count_non_colon():
    text = 'stomach carcinoma'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 0


@pytest.mark.parametrize(('text', 'situ_count', 'maybe_situ_count'), [
    ('adenocarcinoma in situ', 1, 0),
])
def test_carcinoma_in_situ(text, situ_count, maybe_situ_count):
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_in_situ_count() == situ_count
    assert jm.get_carcinoma_in_situ_maybe_count() == maybe_situ_count
