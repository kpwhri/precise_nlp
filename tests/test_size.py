from precise_nlp.const import patterns
from precise_nlp.extract.cspy.finding_builder import FindingBuilder


def test_polyp_size():
    text = 'The polyps were 4 to 6 mm in size'
    exp = 6
    f = FindingBuilder().fsm(text)[0]
    assert f.size == exp


def test_in_size_pattern():
    text = 'The polyps were 4 to 6 mm in size'
    m = patterns.IN_SIZE_PATTERN.search(text)
    assert m
    assert m.group('n1') == '4'
    assert m.group('n2') == '6'
    assert m.group('m') == 'mm'
