#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.utils import _repoze_utils as rpz_utils
from nti.contentsearch.utils import nti_remove_index_zombies as nti_riz

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands

from . import SharedConfiguringTestLayer

@unittest.SkipTest
class TestReindexUserContent(unittest.TestCase):

	layer = SharedConfiguringTestLayer

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
	def test_remove_zombies(self):
		notes, user = self._create_notes()
		self._index_notes(user, notes)
		catsdocs = list(rpz_utils.get_catalog_and_docids(user))
		assert_that(catsdocs, has_length(1))
		assert_that(catsdocs[0][1], has_length(len(zanpakuto_commands)))

		# remove notes
		with user.updates():
			for obj in notes:
				objId = obj.id
				containerId = obj.containerId
				obj = user.getContainedObject(containerId, objId)
				user.deleteContainedObject(containerId, objId)

		catsdocs = list(rpz_utils.get_catalog_and_docids(user))
		assert_that(catsdocs, has_length(1))
		assert_that(catsdocs[0][1], has_length(len(zanpakuto_commands)))

		removed = nti_riz.remove_zombies([user.username])
		assert_that(removed, is_(len(zanpakuto_commands)))

		catsdocs = list(rpz_utils.get_catalog_and_docids(user))
		assert_that(catsdocs[0][1], has_length(0))
