import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.users import DynamicFriendsList
from nti.dataserver.users import interfaces as user_interfaces

from nti.ntiids.ntiids import make_ntiid

import nti.contentsearch
from nti.contentsearch.utils import find_all_indexable_pairs

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands

from nti.tests import ConfiguringTestBase

from hamcrest import (is_, has_length, assert_that)

class TestUtils(ConfiguringTestBase):

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

	def _create_friends_list(self, owner, username='mydfl@nti.com', realname='mydfl', members=() ):
		dfl = DynamicFriendsList(username)
		dfl.creator = owner
		if realname:
			user_interfaces.IFriendlyNamed( dfl ).realname = unicode(realname)

		owner.addContainedObject( dfl )
		for m in members:
			dfl.addFriend( m )
		return dfl

	@WithMockDSTrans
	def test_find_indexable_pairs(self):
		notes, user = self._create_notes()
		pairs = list(find_all_indexable_pairs(user))
		assert_that(pairs, has_length(len(notes)))
		
	@WithMockDSTrans
	def test_find_indexable_pairs_sharedWith(self):
		user_1 = self._create_user(username='nt1@nti.com')
		user_2 = self._create_user(username='nt2@nti.com')
		self._create_note(u'test', user_1, sharedWith=(user_2,))
		pairs = list(find_all_indexable_pairs(user_1))
		assert_that(pairs, has_length(2))
		assert_that(pairs[0][0], is_(user_1))
		assert_that(pairs[1][0], is_(user_2))
		
	@WithMockDSTrans
	def test_find_indexable_pairs_dfl(self):
		user_1 = self._create_user(username='nt1@nti.com')
		user_2 = self._create_user(username='nt2@nti.com')
		user_3 = self._create_user(username='nt3@nti.com')
		dfl = self._create_friends_list(user_1, members=(user_2,))
		self._create_note(u'test', user_1, sharedWith=(dfl, user_3))
		pairs = list(find_all_indexable_pairs(user_1,include_dfls=True))
		assert_that(pairs, has_length(3))
		assert_that(pairs[0][0], is_(user_1))
		assert_that(pairs[1][0], is_(user_3))
		assert_that(pairs[2][0], is_(dfl))
			
if __name__ == '__main__':
	unittest.main()
