import pytest

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.utils import Extent


@pytest.mark.parametrize(('text', 'exp'), [
    ('extent of the procedure: cecum', Extent.COMPLETE),
    ('scope was advanced through the colon to the cecum', Extent.COMPLETE),
    ('visualized the ileocecal valve', Extent.COMPLETE),
    ('visualized the appendiceal orifice', Extent.COMPLETE),
    ('ileum is seen', Extent.COMPLETE),
    ('extent of the procedure', Extent.INCOMPLETE),
    ('extent of the procedure: descending colon', Extent.INCOMPLETE),
    ('terminal ileum not reached', Extent.INCOMPLETE),
    ('ileocecal valve not visualised', Extent.INCOMPLETE),
    ('unable to see the cecum', Extent.INCOMPLETE),
    ('ileum is not seen', Extent.INCOMPLETE),
    ('did not visualize the ileocecal valve', Extent.INCOMPLETE),
    ('did not visualize the appendiceal orifice', Extent.INCOMPLETE),
])
def test_extent(text, exp):
    assert CspyManager(text).get_extent() == exp


@pytest.mark.parametrize(('text', 'exp'), [
    ('appendiceal orifice', Extent.COMPLETE),
    ('ileocecal valve', Extent.COMPLETE),
    ('ileo-cecal valve', Extent.COMPLETE),
    ('cecum', Extent.COMPLETE),
    ('cecum not seen', Extent.INCOMPLETE),
    ('terminal ileum not visualized', Extent.INCOMPLETE),
    ('terminal ileum', Extent.COMPLETE),
    ('did not visualize the ileocecal valve', Extent.INCOMPLETE),
    ('did not visualize the appendiceal orifice', Extent.INCOMPLETE),
])
def test_extent_search_all(text, exp):
    assert CspyManager(text).get_extent(cspy_extent_search_all=True) == exp
