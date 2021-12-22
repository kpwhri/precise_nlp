import pytest

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.utils import Indication


def test_personal_history():
    text = 'Indications: Personal history of colonic polyps'
    exp = Indication.SURVEILLANCE
    assert CspyManager(text).get_indication() == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('Indications: positive hemaccult', Indication.DIAGNOSTIC),
    ('Indications: presents for an EGD for GERD.'
     ' Indications:  presents for a colonoscopy for positive occult blood testing.'
     '  Indications:  presents for an endoscopy for GERD, and a colonoscopy for positive occult blood testing.',
     Indication.DIAGNOSTIC),
])
def test_hemoccult(text, exp):
    assert CspyManager(text).get_indication() == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('Indications: Something here  Instrument: Olympus',
     [' Something here  ']),
    ('Indications: Something here  Patient Active Problem List: ',
     [' Something here  ']),
    ('COLONOSCOPY EXAM\n  \nIndications: Something here  Indications: More here',
     [' Something here  ', ' More here']),
])
def test_indication_section(text, exp):
    assert list(CspyManager(text)._get_section(CspyManager.INDICATIONS)) == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('INDICATIONS: no family members with a history of colon cancer or polyps',
     Indication.UNKNOWN),
    ('INDICATIONS: family members with a history of colon cancer or polyps',
     Indication.SURVEILLANCE),
    ('Indications: FIT + stool: 792.1 - R19.5', Indication.DIAGNOSTIC),
    ('Indications: FIT positive', Indication.DIAGNOSTIC),
    pytest.param(
        '''Indications: * Surveillance due to prior colonic neoplasia (hx of polyps). Suspected serrated polyposis
 syndrome. recurrent polyp In ascending colon on 8/3/17: V12.72 - 286.010''',
        Indication.SURVEILLANCE,
        marks=pytest.mark.xfail(reason='unclear if next item should be handled, etc.')
    ),
    ('Indications: Ulcerative Proctitis: 556.2 - K51.20\nOccult blood in stool: 792.1 - R19.5', Indication.DIAGNOSTIC),
    ('Indications: Ulcerative Proctitis: 556.2 - K51.20\nOccult Blood: 792.1 - R19.5', Indication.DIAGNOSTIC),
    ('Indications: Ulcerative proctitis: 556.2 - K51.20\nOccult Blood: 792.1 - R19.5', Indication.DIAGNOSTIC),
    ('Indications: Personal', Indication.UNKNOWN),
    ('Indications: Follow-up cancer', Indication.SURVEILLANCE),
    ('Indications: Follow-up diverticulitis', Indication.SCREENING),
    ('Indications: Follow-up for diverticulitis', Indication.SCREENING),
    ('Indications: Suspected diverticulitis', Indication.SCREENING),
])
def test_indications(text, exp):
    assert CspyManager(text).get_indication() == exp
