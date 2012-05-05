import time
import uuid
import unittest

from zope import component
from zope.component.hooks import resetHooks

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.externalization.externalization import toExternalObject

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import create_cloudsearch_store
from nti.contentsearch.interfaces import ICloudSearchStore
from nti.contentsearch import _cloudsearch_index as cloudsearch_index
from nti.contentsearch._cloudsearch_userindexmanager import CloudSearchUserIndexManager

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET,
										NTIID, TARGET_OID)

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (is_, is_not, has_key, has_entry, has_length, assert_that)

cloudsearch_index.compute_ngrams = True

@unittest.SkipTest
class TestCloudSearchIndexManager(ConfiguringTestBase):
	
	__name__ = "TestCloudSearchIndexManager"
	
	aws_op_delay = 5
	aws_access_key_id = 'AKIAJ42UUP2EUMCMCZIQ'
	aws_secret_access_key = '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'

	def setUp(self):
		super(TestCloudSearchIndexManager, self).setUp()
		self.user_id = unicode(str(uuid.uuid1()) + '@nti.com')
		self.store = create_cloudsearch_store(self.aws_access_key_id, self.aws_secret_access_key)
		component.provideUtility(self.store, provides=ICloudSearchStore)
		self.cim = CloudSearchUserIndexManager(self.user_id)

	def tearDown(self):
		self._remove_all(self.cim)
		super(TestCloudSearchIndexManager, self).tearDown()
		resetHooks()
		
	def _remove_all(self, cim):
		try:
			cim.remove_index()
		except Exception, e:
			print repr(e)
			pass
		
	# ---------------------
	
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
			note = self.create_note(x, usr.username)
			if conn: conn.add(note)
			notes.append(usr.addContainedObject( note ))
		return notes, usr

	def index_notes(self, dataserver=None, usr=None, conn=None, do_assert=True):
		result = []
		notes, usr = self.add_notes(usr=usr, conn=conn)
		for note in notes:
			resp = self.cim.index_content(note)
			if do_assert: 
				assert_that(resp, is_not(None))
			result.append(resp)
		return notes, result
	
	def add_user_index_notes(self, ds=None):
		usr = User( self.user_id, 'temp' )
		ds = ds or mock_dataserver.current_mock_ds
		ds.root['users'][self.user_id] = usr
		notes, resps = self.index_notes(dataserver=ds, usr=usr, do_assert=False)
		time.sleep(self.aws_op_delay)
		return usr, notes, resps
	
	# ---------------------
	
	@WithMockDSTrans
	def test_query_notes(self):
		self.add_user_index_notes()

		hits = self.cim.search("shield")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'shield'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(1))

		key = list(items.keys())[0]
		hit = toExternalObject(items[key])
		assert_that(hit, has_entry(CLASS, HIT))
		assert_that(hit, has_entry(NTIID, is_not(None)))
		assert_that(hit, has_entry(TARGET_OID, is_not(None)))
		assert_that(key, is_(hit[NTIID]))
		assert_that(hit, has_entry(CONTAINER_ID, 'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(hit, has_entry(SNIPPET, 'all waves rise now and become my SHIELD lightning strike now and become my blade'))

		hits = self.cim.search("*")
		assert_that(hits, has_entry(HIT_COUNT, len(zanpakuto_commands)))

		hits = self.cim.search("?")
		assert_that(hits, has_entry(HIT_COUNT, len(zanpakuto_commands)))

		hits = self.cim.search("ra*")
		assert_that(hits, has_entry(HIT_COUNT, 3))

	@WithMockDSTrans
	def test_update_note(self):
		_, notes, _ = self.add_user_index_notes()
		note = notes[5]
		note.body = [u'Blow It Away']
		self.cim.update_content(note)
		
		time.sleep(self.aws_op_delay)
		
		hits = self.cim.search("shield")
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

		hits = self.cim.search("blow")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'blow'))

	@WithMockDSTrans
	def test_delete_note(self):
		_, notes, _ = self.add_user_index_notes()
		note = notes[5]
		self.cim.delete_content(note)
		
		time.sleep(self.aws_op_delay)
		
		hits = self.cim.search("shield")
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

	@WithMockDSTrans
	def test_ngram_search(self):
		self.add_user_index_notes()
		hits = self.cim.ngram_search("sea")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		
if __name__ == '__main__':
	unittest.main()
