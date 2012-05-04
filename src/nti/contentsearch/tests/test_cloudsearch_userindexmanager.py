import uuid
import unittest

from zope import component
from zope.component.hooks import resetHooks

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.externalization.externalization import toExternalObject

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import create_cloudsearch_store
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch.interfaces import ICloudSearchStore
from nti.contentsearch import _cloudsearch_index as cloudsearch_index
from nti.contentsearch._cloudsearch_userindexmanager import CloudSearchUserIndexManager

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET,
										NTIID, TARGET_OID)

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (is_, is_not, has_key, has_item, has_entry, has_length, assert_that)

cloudsearch_index.compute_ngrams = True

class TestCloudSearchIndexManager(ConfiguringTestBase):
	
	user_id = 'nt@nti.com'
	aws_access_key_id = 'AKIAJ42UUP2EUMCMCZIQ'
	aws_secret_access_key = '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'
	
	def setUp(self):
		super(TestCloudSearchIndexManager, self).setUp()
		self.store = create_cloudsearch_store(self.aws_access_key_id, self.aws_secret_access_key)
		component.provideUtility(self.store, provides=ICloudSearchStore)

	def tearDown(self):
		super(TestCloudSearchIndexManager, self).tearDown()
		resetHooks()
		
	def create_note(self, msg, username, containerId=None):
		note = Note()
		note.creator = username
		note.body = [unicode(msg)]
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note

	def add_notes(self, usr=None, conn=None, messages=zanpakuto_commands):
		notes = []
		conn = conn or mock_dataserver.current_transaction
		usr = usr or User( self.user_id, 'temp' )
		for x in zanpakuto_commands:
			note = self._create_note(x, usr.username)
			if conn: conn.add(note)
			notes.append(usr.addContainedObject( note ))
		return notes, usr

	def index_notes(self, dataserver=None, usr=None, conn=None, do_assert=True):
		result = []
		notes, usr = self._add_notes(usr=usr, conn=conn)
		cim = CloudSearchUserIndexManager (usr.username, self.store.ntisearch)
		for note in notes:
			resp = cim.index_content(note)
			if do_assert: 
				assert_that(resp, is_not(None))
			result.append(resp)
		return cim, notes, result

	def _add_user_index_notes(self, ds=None):
		usr = User( 'nt@nti.com', 'temp' )
		ds = ds or mock_dataserver.current_mock_ds
		ds.root['users']['nt@nti.com'] = usr
		notes, docids, rim = self._index_notes(dataserver=ds, usr=usr, do_assert=False)
		return usr, rim, docids, notes

	@WithMockDSTrans
	def x_test_empty(self):
		user_id = str(uuid.uuid1())
		rim = CloudSearchUserIndexManager(user_id, self.store.ntisearch)
		assert_that(rim.get_stored_indices(), is_(list(indexable_type_names)))
		assert_that(rim.has_stored_indices(), is_(False))
		


if __name__ == '__main__':
	unittest.main()
