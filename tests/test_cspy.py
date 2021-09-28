import pytest

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.utils import Extent, Prep, Indication


@pytest.mark.parametrize(('text', 'exp'), [
    ('video colonoscope was inserted into the rectum and advanced through a well prepared colon '
     'to the cecum, as determined by seeing the ileocecal valve and the cecal tip.     Extent of '
     'Procedure: cecum', Extent.COMPLETE)
])
def test_extent(text, exp):
    assert CspyManager(text).get_extent() == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('video colonoscope was inserted into the rectum and advanced through a well prepared colon '
     'to the cecum, as determined by seeing the ileocecal valve and the cecal tip.     Extent of '
     'Procedure: cecum', Prep.ADEQUATE),
    ('fair preparation', Prep.INADEQUATE),
    ('suboptimal preparation', Prep.INADEQUATE),
])
def test_prep(text, exp):
    assert CspyManager(text).get_prep() == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('COLONOSCOPY     INDICATIONS: 2 adenomas found on screening flex sig    Procedure(s) performed: COLONOSCOPY    '
     'Instrument: video colonoscope', Indication.SCREENING),
    ('COLONOSCOPY   EGD Indications: abdominal pain  Colonoscopy Indications: screening for colonic neoplasia'
     ' Procedure(s) performed: COLONOSCOPY Instrument: video colonoscope', Indication.SCREENING),
])
def test_indication(text, exp):
    assert CspyManager(text).get_indication() == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('Screening for colonic neoplasia; diverticulitis of large intestine', Indication.SCREENING),
])
def test_indication_section(text, exp):
    assert CspyManager(text)._get_indications_from([text]) == exp
