import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

import nti.contentsearch
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.utils import nti_reindex_user_content as nti_ruc

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands

from nti.tests import ConfiguringTestBase

from hamcrest import (has_length, assert_that)

class TestReindexUserContent(ConfiguringTestBase):

	set_up_packages = (nti.dataserver, nti.contentsearch)
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	def _create_note(self, msg, owner, containerId=None, sharedWith=()):
		note = Note()
		note.creator = owner
		note.body = [unicode(msg)]
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		for s in sharedWith or ():
			note.addSharingTarget(s)
		mock_dataserver.current_transaction.add(note)
		note = owner.addContainedObject( note ) 
		return note

	def _create_notes(self, usr=None, sharedWith=()):
		notes = []
		usr = usr or self._create_user()
		for msg in zanpakuto_commands:
			note = self._create_note(msg, usr, sharedWith=sharedWith)
			notes.append(note)
		return notes, usr

	def _index_notes(self, usr, notes):
		docids = []
		rim = search_interfaces.IRepozeEntityIndexManager(usr)
		for note in notes:
			docid = rim.index_content(note)
			docids.append(docid)
		return docids
	
	@WithMockDSTrans
	def test_reindex(self):
		notes, user = self._create_notes()
		self._index_notes(user, notes)
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		hits = rim.search("shoot")
		assert_that(hits, has_length(1))
		catfield = list(rim.get('note').values())[0]
		assert_that(list(catfield._indexed()), has_length(len(zanpakuto_commands)))
				
		# remove catalog
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		rim.pop('note')
		hits = rim.search("shoot")
		assert_that(hits, has_length(0))
		
		# reindex all
		nti_ruc.reindex_entity_content(user)
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		hits = rim.search("shoot")
		assert_that(hits, has_length(1))
		catfield = list(rim.get('note').values())[0]
		assert_that(list(catfield._indexed()), has_length(len(zanpakuto_commands)))
		
if __name__ == '__main__':
	unittest.main()
