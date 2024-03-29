import pytest

from precise_nlp.const.enums import AssertionStatus
from precise_nlp.extract.path import JarManager


@pytest.fixture
def jm():
    return JarManager()


@pytest.mark.parametrize('text, exp, exp_maybe', [
    ('C. COLON, ASCENDING MASS, BIOPSY:\n- Adenocarcinoma.', 1, 0),
    ('adenosquamous carcinoma', 1, 0),
])
def test_carcinoma_count(jm, text, exp, exp_maybe):
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == exp_maybe
    assert jm.get_carcinoma_count() == exp


def test_carcinoma_maybe_count(jm):
    text = 'suspicious for adenosquamous carcinoma'
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 1
    assert jm.get_carcinoma_count() == 0


def test_carcinoma_value(jm):
    text = 'suspicious for adenosquamous carcinoma'
    jm.cursory_diagnosis_examination(text)
    jar = jm.get_current_jar()
    assert jar.carcinoma_list[0][0] == 'adenosquamous carcinoma'
    assert jar.carcinoma_list[0][1] == AssertionStatus.PROBABLE


def test_carcinoma_count_rectal_melanoma(jm):
    text = 'rectal, adenoma, melanoma'
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 1


def test_carcinoma_count_colonic_melanoma(jm):
    text = 'descending, adenoma, melanoma'
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 0


def test_carcinoma_count_non_colon(jm):
    text = 'stomach carcinoma'
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_maybe_count() == 0
    assert jm.get_carcinoma_count() == 0


@pytest.mark.parametrize(('text', 'situ_count', 'maybe_situ_count', 'possible_situ_count'), [
    ('adenocarcinoma in situ', 1, 0, 0),
    ('possible adenocarcinoma in situ', 0, 0, 1),
    ('probable adenocarcinoma in situ', 0, 1, 1),
    ('probable adenocarcinoma in-situ', 0, 1, 1),
    ('in-situ squamous cell carcinoma', 1, 0, 0),
    ('in situ squamous cell carcinoma', 1, 0, 0),
    # the next two are made up to ensure 'in' is not skipped
    ('probable signet ring squamous cell in situ carcinoma', 0, 1, 1),
    ('probable signet ring squamous cell in-situ carcinoma', 0, 1, 1),
])
def test_carcinoma_in_situ(jm, text, situ_count, maybe_situ_count, possible_situ_count):
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_in_situ_count() == situ_count
    assert jm.get_carcinoma_in_situ_maybe_count(probable_only=True) == maybe_situ_count
    assert jm.get_carcinoma_in_situ_maybe_count() == possible_situ_count


@pytest.mark.parametrize('text', [
    'melanosis coli',
    'negative for neoplasm',
    'previous colon cancer',
    pytest.param(
        'History of malignant neoplasm',
        marks=pytest.mark.xfail(reason='not going to handle this right now; from other section')
    ),
])
def test_negatives_carcinoma(jm, text):
    jm.cursory_diagnosis_examination(text)
    assert jm.get_carcinoma_count() == 0


@pytest.mark.parametrize('text, exp', [
    ('Adenomatous polyp not identified', 0),
    ('Adenomatous polyp', 1),
    # the next one is negation by way of 'sessile serrated adenoma'
    ('Negative for diagnostic features of sessile serrated adenoma, dysplasia or invasive malignancy (see comment)', 0),
    ('Negative for diagnostic features of adenoma, dysplasia or invasive malignancy (see comment)', 0),
    ('Negative for diagnostic features of dysplasia, adenoma or invasive malignancy (see comment)', 0),
    ('Negative for diagnostic features of dysplasia, malignancy or adenoma (see comment)', 0),
])
def test_negatives_adenoma(jm, text, exp):
    jm.cursory_diagnosis_examination(text)
    assert jm.get_adenoma_count().count == exp


@pytest.mark.parametrize('text, exp', [
    ('Negative for diagnostic features of sessile serrated adenoma, dysplasia or invasive malignancy (see comment)', 0),

])
def test_negatives_ssp(jm, text, exp):
    jm.cursory_diagnosis_examination(text)
    assert jm.get_sessile_serrated_count() == exp


@pytest.mark.parametrize('text, count', [
    ('COLON, DESCENDING POLYPS, POLYPECTOMY.\n- Tubular adenomas', 2),
    pytest.param(
        'ASCENDING POLYPS, POLYPECTOMY:\n - Tubular adenoma, 2 of fragments.', 2,
        marks=pytest.mark.xfail(reason='chart abstraction has the below as 2, but I\'m not clear anymore')
    ),
])
def test_adenoma_jar_gte(jm, text, count):
    jm.cursory_diagnosis_examination(text)
    maybe_counter = jm.get_adenoma_count()
    assert maybe_counter.at_least is True
    assert maybe_counter.greater_than is False
    assert maybe_counter.count == count
