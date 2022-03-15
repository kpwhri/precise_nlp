from precise_nlp.extract.cspy import CspyManager


def test_deenumerate():
    text = '1'
    res = CspyManager('1', test_skip_parse=True)._deenumerate(text)
    assert res == []
