import os
import time
import uuid
import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.externalization.externalization import toExternalObject

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET,
										NTIID, TARGET_OID)

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (is_not, has_key, has_entry, has_length, assert_that)

@unittest.SkipTest
class TestCloudSearchAdapter(ConfiguringTestBase):
	
	__name__ = "TestCloudSearchAdapter"
	
	aws_op_delay = 5
	aws_access_key_id = 'AKIAJ42UUP2EUMCMCZIQ'
	aws_secret_access_key = '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'

	@classmethod
	def setUpClass(cls):
		os.environ['aws_access_key_id']= cls.aws_access_key_id
		os.environ['aws_secret_access_key']= cls.aws_secret_access_key
		
	# ---------------------
	
	def create_note(self, msg, username, containerId=None):
		note = Note()
		note.creator = username
		note.body = [unicode(msg)]
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note

	def add_notes(self, usr, messages=zanpakuto_commands):
		notes = []
		conn = mock_dataserver.current_transaction
		for x in zanpakuto_commands:
			note = self.create_note(x, usr.username)
			if conn: conn.add(note)
			note = usr.addContainedObject( note )
			notes.append(note)
		return notes

	def index_notes(self, usr, do_assert=True):
		result = []
		notes = self.add_notes(usr=usr)
		cim = search_interfaces.ICloudSearchEntityIndexManager(usr)
		for note in notes:
			resp = cim.index_content(note)
			if do_assert: 
				assert_that(resp, is_not(None))
			result.append(resp)
		return notes, result
	
	def add_user_index_notes(self):
		username = unicode(str(uuid.uuid1())) + '@nti.com' 
		usr = User.create_user(mock_dataserver.current_mock_ds, username=username, password='temp001' )
		notes, resps = self.index_notes(usr=usr, do_assert=False)
		time.sleep(self.aws_op_delay)
		return usr, notes, resps
	
	# ---------------------
	
	@WithMockDSTrans
	def test_query_notes(self):
		usr, _, _ = self.add_user_index_notes()
		cim = search_interfaces.ICloudSearchEntityIndexManager(usr)
		
		results = cim.search("shield")
		hits = toExternalObject (results)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'shield'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(1))
		hit = items[0]
		assert_that(hit, has_entry(CLASS, HIT))
		assert_that(hit, has_entry(NTIID, is_not(None)))
		assert_that(hit, has_entry(TARGET_OID, is_not(None)))
		assert_that(hit, has_entry(CONTAINER_ID, 'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(hit, has_entry(SNIPPET, 'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))

		hits = toExternalObject(cim.search("*"))
		assert_that(hits, has_entry(HIT_COUNT, len(zanpakuto_commands)))

		hits = toExternalObject(cim.search("?"))
		assert_that(hits, has_entry(HIT_COUNT, len(zanpakuto_commands)))

		hits = toExternalObject(cim.search("ra*"))
		assert_that(hits, has_entry(HIT_COUNT, 3))

	@WithMockDSTrans
	def test_update_note(self):
		usr, notes, _ = self.add_user_index_notes()
		cim = search_interfaces.ICloudSearchEntityIndexManager(usr)
		
		note = notes[5]
		note.body = [u'Blow It Away']
		cim.update_content(note)
		time.sleep(self.aws_op_delay)
		
		hits = toExternalObject(cim.search("shield"))
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

		hits = toExternalObject(cim.search("blow"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'blow'))

	@WithMockDSTrans
	def test_delete_note(self):
		usr, notes, _ = self.add_user_index_notes()
		cim = search_interfaces.ICloudSearchEntityIndexManager(usr)
		note = notes[5]
		cim.delete_content(note)
		time.sleep(self.aws_op_delay)
		hits = toExternalObject(self.cim.search("shield"))
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

	@WithMockDSTrans
	def test_ngram_search(self):
		usr, _, _ = self.add_user_index_notes()
		cim = search_interfaces.ICloudSearchEntityIndexManager(usr)
		hits = toExternalObject(cim.ngram_search("sea"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		
if __name__ == '__main__':
	unittest.main()
