import unittest


from ZODB import DB
from ZODB.MappingStorage import MappingStorage
import transaction

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

	def setUp(self):
		super(TestDataStore, self).setUp()
		self.storage = MappingStorage()
		self.db = DB(self.storage)

	def tearDown(self):
		super(TestDataStore, self).tearDown()
		self.db.close()

	def test_ctor(self):
		store = RepozeDataStore(self.db, users_key='_users_', docMap_key='_docMap_')
		assert_that(store, has_key('_users_'))
		assert_that(store, has_key('_docMap_'))
		assert_that(store['_users_'], is_not(None))
		assert_that(store['_docMap_'], is_not(None))

	def test_add_get_catalog(self):
		catalog = create_notes_catalog()
		store = RepozeDataStore(self.db)


		transaction.begin()
		with store.dbTrans():
			store.add_catalog('nt@nt.com', catalog, 'note')
		transaction.commit()

		with store.dbTrans():
			c = store.get_catalog('nt@nt.com', 'note')
			assert_that(c, is_not(None))
		transaction.commit()

		with store.dbTrans():
			c = store.get_catalog('nt@nt.com', 'xxxx')
			assert_that(c, is_(None))

			c = store.get_catalog('nt2@nt.com', 'note')
			assert_that(c, is_(None))
		transaction.commit()

	def test_get_catalogs(self):
		store = RepozeDataStore(self.db)
		with store.dbTrans():
			for u in xrange(10):
				username  = 'nt_%s@nt.com' % u
				for t in xrange(5):
					type_ = 'highlight_%s' % t
					store.add_catalog(username, create_highlight_catalog(), type_)
		transaction.commit()

		with store.dbTrans():
			for u in xrange(10):
				username  = 'nt_%s@nt.com' % u
				obj = store.get_catalog_names(username)
				assert_that(obj, has_length(5))

				obj = store.get_catalogs(username)
				assert_that(obj, has_length(5))
		transaction.commit()

	def test_remove_catalogs(self):
		store = RepozeDataStore(self.db)
		username  = 'nt@nt.com'

		with store.dbTrans():
			for t in xrange(5):
				type_ = 'message_info_%s' % t
				store.add_catalog(username, create_messageinfo_catalog(), type_)
		transaction.commit()
		with store.dbTrans():
			type_ = 'message_info_0'
			store.remove_catalog(username, type_)
		transaction.commit()

		with store.dbTrans():
			type_ = 'message_info_0'
			c = store.get_catalog(username, type_)
			assert_that(c, is_(None))

			obj = store.get_catalog_names(username)
			assert_that(obj, has_length(4))
		transaction.commit()

if __name__ == '__main__':
	unittest.main()
