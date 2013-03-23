#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight

from nti.ntiids.ntiids import make_ntiid

from ...constants import highlight_
from ... import interfaces as search_interfaces

from .. import _repoze_utils as rpz_utils
from .. import nti_reindex_entity_content as nti_ruc

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands

from . import ConfiguringTestBase

from hamcrest import (has_length, assert_that)

class TestReindexUserContent(ConfiguringTestBase):

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

	def _create_highlights(self, usr=None, sharedWith=()):
		result = []
		usr = usr or self._create_user()
		for msg in zanpakuto_commands:
			hi = self._create_highlight(msg, usr, sharedWith=sharedWith)
			result.append(hi)
		return result, usr

	def _index_objects(self, usr, objects):
		docids = []
		rim = search_interfaces.IRepozeEntityIndexManager(usr)
		for obj in objects:
			docid = rim.index_content(obj)
			docids.append(docid)
		return docids

	@WithMockDSTrans
	def test_reindex(self):
		notes, user = self._create_notes()
		self._index_objects(user, notes)
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		hits = rim.search("shoot")
		assert_that(hits, has_length(1))

		catsdocs = list(rpz_utils.get_catalog_and_docids(user))
		assert_that(catsdocs, has_length(1))
		assert_that(catsdocs[0][1], has_length(len(zanpakuto_commands)))

		# remove catalog
		rpz_utils.remove_entity_catalogs(user)
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		assert_that(rim, has_length(0))

		hits = rim.search("shoot")
		assert_that(hits, has_length(0))

		# reindex all
		nti_ruc.reindex_entity_content(user)
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		hits = rim.search("shoot")
		assert_that(hits, has_length(1))
		catsdocs = list(rpz_utils.get_catalog_and_docids(user))
		assert_that(catsdocs[0][1], has_length(len(zanpakuto_commands)))

	@WithMockDSTrans
	def test_reindex_highlights(self):
		notes, user = self._create_notes()
		his, _ = self._create_highlights(user)
		self._index_objects(user, notes)
		self._index_objects(user, his)

		rim = search_interfaces.IRepozeEntityIndexManager(user)
		assert_that(rim, has_length(2))

		hits = rim.search("shoot")
		assert_that(hits, has_length(2))

		# remove catalog
		rpz_utils.remove_entity_catalogs(user, (highlight_,))
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		assert_that(rim, has_length(1))

		hits = rim.search("shoot")
		assert_that(hits, has_length(1))

		# reindex highlights
		nti_ruc.reindex_entity_content(user, highlight_)
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		hits = rim.search("shoot")
		assert_that(hits, has_length(2))
