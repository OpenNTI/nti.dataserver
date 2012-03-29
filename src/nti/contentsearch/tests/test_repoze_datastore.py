import unittest

from nti.contentsearch._repoze_datastore import RepozeDataStore
from nti.contentsearch._repoze_index import create_notes_catalog
from nti.contentsearch._repoze_index import create_highlight_catalog
from nti.contentsearch._repoze_index import create_messageinfo_catalog

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_length

class TestDataStore(ConfiguringTestBase):

	def test_ctor(self):
		store = RepozeDataStore(users_key='_users_', docMap_key='_docMap_')
		assert_that(store, has_key('_users_'))
		assert_that(store, has_key('_docMap_'))
		assert_that(store['_users_'], is_not(None))
		assert_that(store['_docMap_'], is_not(None))

	def test_add_get_catalog(self):
		catalog = create_notes_catalog()
		store = RepozeDataStore()

		store.add_catalog('nt@nt.com', catalog, 'note')
		c = store.get_catalog('nt@nt.com', 'note')
		assert_that(c, is_not(None))
		
		c = store.get_catalog('nt@nt.com', 'xxxx')
		assert_that(c, is_(None))

		c = store.get_catalog('nt2@nt.com', 'note')
		assert_that(c, is_(None))
		
	def test_get_catalogs(self):
		store = RepozeDataStore()
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
		store = RepozeDataStore()
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
		
	def test_docmap(self):
		store = RepozeDataStore()
		username = u'nt@nt.com'
		address = u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'
		store.add_catalog(username, create_notes_catalog(), 'note')
		
		docid = store.add_address(username, address)
		assert_that(docid, is_not(None))
		
		xaddress = store.address_for_docid(username, docid)
		assert_that(xaddress, is_(address))
		
		xdocid = store.docid_for_address(username, address)
		assert_that(xdocid, is_(docid))
		
		counter = 0
		docids = store.get_docids(username)
		for _ in docids:
			counter = counter + 1 
		assert_that(counter, is_(1))
		
		store.remove_docid(username, docid)
		
		xdocid = store.docid_for_address(username, address)
		assert_that(xdocid, is_(None))
		
		xaddress = store.address_for_docid(username, docid)
		assert_that(xaddress, is_(None))
		
		counter = 0
		docids = store.get_docids(username)
		for _ in docids:
			counter = counter + 1 
		assert_that(counter, is_(0))
		
if __name__ == '__main__':
	unittest.main()
