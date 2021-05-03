from precise_nlp.extract.path import JarManager


def test_dysplasia_negation():
    text = 'negative for high grade dysplasia'
    jm = JarManager()
    jm.cursory_diagnosis_examination(text)
    assert jm.has_dysplasia() == 0
