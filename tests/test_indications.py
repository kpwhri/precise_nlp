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
])
def test_indications(text, exp):
    assert CspyManager(text).get_indication() == exp
