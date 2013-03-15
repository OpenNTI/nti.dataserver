#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver import users
from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight
from nti.dataserver.users import DynamicFriendsList
from nti.dataserver.users import interfaces as user_interfaces

from nti.ntiids.ntiids import make_ntiid

from .. import find_all_notes
from .. import find_all_highlights
from .. import find_all_indexable_pairs
from ...constants import note_, redaction_
from ... import interfaces as search_interfaces
from .._repoze_utils import remove_entity_catalogs

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import zanpakuto_commands
from . import ConfiguringTestBase

from hamcrest import (assert_that, is_not, has_key, has_length, has_item)

class TestUtils(ConfiguringTestBase):

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	def _create_note(self, msg, owner, containerId=None, sharedWith=()):
		note = Note()
		note.creator = owner
		note.body = [unicode(msg)]
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		for s in sharedWith or ():
			note.addSharingTarget(s)
		mock_dataserver.current_transaction.add(note)
		note = owner.addContainedObject(note)
		return note

	def _create_highlight(self, msg, owner, containerId=None, sharedWith=()):
		highlight = Highlight()
		highlight.selectedText = unicode(msg)
		highlight.creator = owner.username
		highlight.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		for s in sharedWith or ():
			highlight.addSharingTarget(s)
		mock_dataserver.current_transaction.add(highlight)
		highlight = owner.addContainedObject(highlight)
		return highlight

	def _create_notes(self, usr=None, sharedWith=()):
		notes = []
		usr = usr or self._create_user()
		for msg in zanpakuto_commands:
			note = self._create_note(msg, usr, sharedWith=sharedWith)
			notes.append(note)
		return notes, usr

	def _create_highlights(self, usr=None, sharedWith=()):
		result = []
		usr = usr or self._create_user()
		for msg in zanpakuto_commands:
			hi = self._create_highlight(msg, usr, sharedWith=sharedWith)
			result.append(hi)
		return result, usr

	def _create_notes_and_index(self, usr=None, sharedWith=()):
		notes, usr = self._create_notes(usr, sharedWith)
		rim = search_interfaces.IRepozeEntityIndexManager(usr)
		for n in notes:
			rim.index_content(n)
		return notes, usr

	def _create_friends_list(self, owner, username='mydfl@nti.com', realname='mydfl', members=()):
		dfl = DynamicFriendsList(username)
		dfl.creator = owner
		if realname:
			user_interfaces.IFriendlyNamed(dfl).realname = unicode(realname)

		owner.addContainedObject(dfl)
		for m in members:
			dfl.addFriend(m)
		return dfl

	@WithMockDSTrans
	def test_remove_entity_catalogs(self):
		_, user = self._create_notes_and_index()
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		assert_that(rim, has_key(note_))
		remove_entity_catalogs(user, (redaction_))
		assert_that(rim, has_key(note_))
		remove_entity_catalogs(user, (note_))
		assert_that(rim, is_not(has_key(note_)))

	@WithMockDSTrans
	def test_find_indexable_pairs(self):
		notes, user = self._create_notes()
		pairs = list(find_all_indexable_pairs(user))
		assert_that(pairs, has_length(len(notes)))

	@WithMockDSTrans
	def test_find_all_notes(self):
		notes, user = self._create_notes()
		pairs = list(find_all_notes(user))
		assert_that(pairs, has_length(len(notes)))
		pairs = list(find_all_highlights(user))
		assert_that(pairs, has_length(0))

	@WithMockDSTrans
	def test_find_all_highlights(self):
		his, user = self._create_highlights()
		pairs = list(find_all_highlights(user))
		assert_that(pairs, has_length(len(his)))

	@WithMockDSTrans
	def test_find_indexable_pairs_sharedWith(self):
		user_1 = self._create_user(username='nt1@nti.com')
		user_2 = self._create_user(username='nt2@nti.com')
		self._create_note(u'test', user_1, sharedWith=(user_2,))
		pairs = list(find_all_indexable_pairs(user_1))
		assert_that(pairs, has_length(2))
		assert_that(pairs, has_item(has_item(user_1)))
		assert_that(pairs, has_item(has_item(user_2)))

	@WithMockDSTrans
	def test_find_indexable_pairs_dfl(self):
		self.ds.add_change_listener(users.onChange)

		user_1 = self._create_user(username='nt1@nti.com')
		user_2 = self._create_user(username='nt2@nti.com')
		user_3 = self._create_user(username='nt3@nti.com')
		dfl = self._create_friends_list(user_1, members=(user_2,))
		self._create_note(u'test', user_1, sharedWith=(dfl, user_3))
		pairs = list(find_all_indexable_pairs(user_1))

		__traceback_info__ = pairs
		assert_that(pairs, has_length(4))
		assert_that(pairs, has_item(has_item(user_1)))
		assert_that(pairs, has_item(has_item(user_2)))
		assert_that(pairs, has_item(has_item(user_3)))
		assert_that(pairs, has_item(has_item(dfl)))

	test_find_indexable_pairs_dfl.with_ds_changes = True
