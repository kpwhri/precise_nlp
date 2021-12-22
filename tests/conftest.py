import pytest

from precise_nlp.extract.cspy import CspyManager


@pytest.fixture
def cspy():
    """Sets up CspyManager for use in calling its functions"""
    return CspyManager('', test_skip_parse=True)
