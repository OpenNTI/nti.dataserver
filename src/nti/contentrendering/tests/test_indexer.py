
from zope import component

from nti.contentrendering import interfaces as cr_interfaces

from nti.contentrendering.tests import ConfiguringTestBase

from hamcrest import assert_that, is_not

class TestIndexer(ConfiguringTestBase):

	def test_index_utils(self):
		indexer = component.getUtility(cr_interfaces.IBookIndexer)
		assert_that(indexer, is_not(None))

		indexer = component.getUtility(cr_interfaces.IBookIndexer, name="whoosh.file")
		assert_that(indexer, is_not(None))
