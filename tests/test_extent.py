import pytest

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.utils import Extent


@pytest.mark.parametrize(('text', 'exp'), [
    ('extent of the procedure: cecum', Extent.COMPLETE),
    ('scope was advanced through the colon to the cecum', Extent.COMPLETE),
    ('visualized the ileocecal valve', Extent.COMPLETE),
    ('visualized the appendiceal orifice', Extent.COMPLETE),
    ('ileum is seen', Extent.COMPLETE),
])
def test_extent(text, exp):
    assert CspyManager(text).get_extent() == exp
