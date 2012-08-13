import unittest

from zope import component

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Redaction
from nti.externalization.externalization import toExternalObject

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET,
										NTIID, TARGET_OID)

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (is_, is_not, has_key, has_item, has_entry, has_length, assert_that)

class TestRepozeUserIndexManager(ConfiguringTestBase):

	def is_ngram_search_supported(self):
		features = component.getUtility(search_interfaces.ISearchFeatures)
		return features.is_ngram_search_supported
	
	def is_word_suggest_supported(self):
		features = component.getUtility(search_interfaces.ISearchFeatures)
		return features.is_word_suggest_supported
	
	def _create_note(self, msg, username, containerId=None):
		note = Note()
		note.body = [unicode(msg)]
		note.creator = username
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note

	def _add_notes(self, usr=None, conn=None):
		notes = []
		conn = conn or mock_dataserver.current_transaction
		usr = usr or User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		for x in zanpakuto_commands:
			note = self._create_note(x, usr.username)
			if conn: conn.add(note)
			note = usr.addContainedObject( note ) 
			notes.append(note)
		return notes, usr

	def _index_notes(self, dataserver=None, usr=None, conn=None, do_assert=True):
		docids = []
		notes, usr = self._add_notes(usr=usr, conn=conn)
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		for note in notes:
			docid = rim.index_content(note)
			if do_assert:
				assert_that(docid, is_not(None))
			docids.append(docids)
		return usr, notes, docids

	def _add_user_index_notes(self, ds=None):
		usr = User.create_user( ds, username='nt@nti.com', password='temp' )
		_, notes, docids = self._index_notes(dataserver=ds, usr=usr, do_assert=False)
		return usr, docids, notes

	@WithMockDSTrans
	def test_empty(self):
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		assert_that(rim.get_stored_indices(), is_([]))
		assert_that(rim.has_stored_indices(), is_(False))

	@WithMockDSTrans
	def test_index_notes(self):
		usr, _, _, = self._index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		assert_that(rim.get_stored_indices(), is_([u'note']))
		assert_that(rim.has_stored_indices(), is_(True))

	@WithMockDSTrans
	def test_delete_catalog(self):
		usr, _, _, = self._index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		assert_that(rim.get_stored_indices(), is_([u'note']))
		rim.remove_index('note')
		assert_that(rim.get_stored_indices(), is_([]))

	@WithMockDSTrans
	def test_query_notes(self):
		usr, _, _ = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		
		hits = rim.search("shield", limit=None)
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
		assert_that(hit, has_entry(SNIPPET, 'All Waves Rise now and Become my SHIELD Lightning Strike now and Become my Blade'))

		hits = rim.search("*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))

		hits = rim.search("?", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))

		hits = rim.search("ra*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 3))

	@WithMockDSTrans
	def test_update_note(self):
		usr, _, notes = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		note = notes[5]
		note.body = [u'Blow It Away']
		rim.update_content(note)

		hits = rim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

		hits = rim.search("blow", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'blow'))

	@WithMockDSTrans
	def test_delete_note(self):
		usr, _, notes = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		
		note = notes[5]
		rim.delete_content(note)

		hits = rim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

	@WithMockDSTrans
	def test_suggest(self):
		
		if not self.is_word_suggest_supported():
			return
		
		usr, _, _ = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		
		hits = rim.suggest("ra")
		assert_that(hits, has_entry(HIT_COUNT, 4))
		assert_that(hits, has_entry(QUERY, 'ra'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(4))
		assert_that(items, has_item('rankle'))
		assert_that(items, has_item('raise'))
		assert_that(items, has_item('rain'))
		assert_that(items, has_item('rage'))

	@WithMockDSTrans
	def test_ngram_search(self):
		
		if not self.is_ngram_search_supported():
			return
		
		usr, _, _ = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		
		hits = rim.ngram_search("sea")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))

	@mock_dataserver.WithMockDS
	def test_note_index_to_two_users(self):
		ds = mock_dataserver.current_mock_ds
		users = []
		with mock_dataserver.mock_db_trans( ds ):
			for x in range(2):
				username = 'nt%s@nti.com' % x
				user = User.create_user( ds, username=username, password='temp' )
				users.append(user)

			note = self._create_note('ichigo', users[0].username)
			note = users[0].addContainedObject( note )

		rims = []
		for x in range(2):
			with mock_dataserver.mock_db_trans( ds ):
				usr = users[x]
				rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
				rims.append(rim)
				rim.index_content(note)

		for x in xrange(2):
			with mock_dataserver.mock_db_trans( ds ):
				hits = rims[x].search("ichigo", limit=None)
				assert_that(hits, has_entry(HIT_COUNT, 1))

	@WithMockDSTrans
	def test_create_redaction(self):
		username = 'kuchiki@bleach.com'
		user = User.create_user(mock_dataserver.current_mock_ds, username=username, password='temp' )
		redaction = Redaction()
		redaction.selectedText = u'Fear'
		redaction.replacementContent = 'Ichigo'
		redaction.redactionExplanation = 'Have overcome it everytime I have been on the verge of death'
		redaction.creator = username
		redaction.containerId = make_ntiid(nttype='bleach', specific='manga')
		redaction = user.addContainedObject( redaction )
		
		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
		docid = rim.index_content(redaction)
		assert_that(docid, is_not(None))
		
		hits = rim.search("fear", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		
		hits = rim.search("death", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		
		hits = rim.search("ichigo", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
				
if __name__ == '__main__':
	unittest.main()
