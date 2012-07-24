import unittest

from nti.contentsearch import create_repoze_datastore
from nti.contentsearch._repoze_index import create_notes_catalog
from nti.contentsearch._repoze_index import create_highlight_catalog
from nti.contentsearch._repoze_index import create_messageinfo_catalog

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

class TestDataStore(ConfiguringTestBase):

	def test_add_get_catalog(self):
		catalog = create_notes_catalog()
		store = create_repoze_datastore()

		store.add_catalog('nt@nt.com', catalog, 'note')
		c = store.get_catalog('nt@nt.com', 'note')
		assert_that(c, is_not(None))
		
		c = store.get_catalog('nt@nt.com', 'xxxx')
		assert_that(c, is_(None))

		c = store.get_catalog('nt2@nt.com', 'note')
		assert_that(c, is_(None))
		
	def test_get_catalogs(self):
		store = create_repoze_datastore()
		for u in xrange(10):
			username  = 'nt_%s@nt.com' % u
			for t in xrange(5):
				type_ = 'highlight_%s' % t
				store.add_catalog(username, create_highlight_catalog(), type_)
		
		for u in xrange(10):
			username  = 'nt_%s@nt.com' % u
			obj = store.get_catalog_names(username)
			assert_that(obj, has_length(5))

			obj = store.get_catalogs(username)
			assert_that(obj, has_length(5))
		
	def test_remove_catalogs(self):
		store = create_repoze_datastore()
		username  = 'nt@nt.com'

		for t in xrange(5):
			type_ = 'message_info_%s' % t
			store.add_catalog(username, create_messageinfo_catalog(), type_)
		
		type_ = 'message_info_0'
		store.remove_catalog(username, type_)
		
		type_ = 'message_info_0'
		c = store.get_catalog(username, type_)
		assert_that(c, is_(None))

		obj = store.get_catalog_names(username)
		assert_that(obj, has_length(4))
		

if __name__ == '__main__':
	unittest.main()
