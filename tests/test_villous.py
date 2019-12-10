import pytest

from precise_nlp.const.enums import Histology
from precise_nlp.extract.path import JarManager


@pytest.mark.parametrize(('path', 'result'), [
    # negation
    ('biopsy: no villous blunting or significant inflammation identified', 0),
    ('no adenomatous or villous changes present', 0),
    ('no evidence of residual villous adenoma', 0),
    # location
    ('duodenum, biopsy: intact normal villous architecture', 0),
    ('biopsy: intact normal villous architecture', 1),
    ('small bowel: intact normal villous architecture', 0),
    # other
    ('colon, descending, biopsy: 1. tubular adenoma. 2. tubulovillous adenomatous polyp', 1),
    ('villotubular adenoma', 1),
    ('mixed tubular and villiform adenoma', 1),
    ('tubulovil', 1),
])
def test_villous_text(path, result):
    jm = JarManager()
    jm.cursory_diagnosis_examination(path)
    tbv = jm.get_histology(Histology.TUBULOVILLOUS)
    vil = jm.get_histology(Histology.VILLOUS)
    assert tbv[0] or vil[0] == result


@pytest.mark.parametrize(('path', 'result', 'index'), [
    ('rectosig: villous', 0, 4),  # unknown
    ('segment, sigmoid colon and rectum: villous adenoma', 0, 2),  # distal
    ('designated "residual rectal polyp" fragments of mixed tubular and villiform adenoma', 0, 2),  # distal
    ('prox transv colon & 35cm:tubulovil adenoma', 0, 1),  # proximal
    ('colon, cecum, biopsy: tubulovillous adenoma', 1, 1),  # proximal
])
def test_villous_location(path, result, index):
    """

    :param path:
    :param result:
    :param index:
        * 0 - any
        * 1 - proximal
        * 2 - distal
        * 3 - rectal
        * 4 - unknown
    :return:
    """
    jm = JarManager()
    jm.cursory_diagnosis_examination(path)
    tbv = jm.get_histology(Histology.TUBULOVILLOUS)
    vil = jm.get_histology(Histology.VILLOUS)
    assert tbv[index] or vil[index] == result
