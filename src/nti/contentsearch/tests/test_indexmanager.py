#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import os
import time
import uuid
import shutil
import tempfile
from datetime import datetime

from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.contenttypes import Note
from nti.dataserver.users import DynamicFriendsList

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from .._search_query import QueryObject
from .._whoosh_index import create_book_schema
from .._whoosh_indexstorage import create_directory_index
from ..indexmanager import create_index_manager_with_repoze
from ..indexmanager import create_index_manager_with_whoosh
from .._whoosh_bookindexmanager import WhooshBookIndexManager

from ..constants import (ITEMS, HIT_COUNT)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import phrases
from . import zanpakuto_commands
from . import ConfiguringTestBase

from hamcrest import (is_, assert_that, has_length, has_entry)

class _BaseIndexManagerTest(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(_BaseIndexManagerTest,cls).setUpClass()
		cls.now = time.time()
		cls._add_book_data()

	@classmethod
	def _add_book_data(cls):
		cls.now = time.time()
		cls.book_idx_dir = tempfile.mkdtemp(dir="/tmp")
		create_directory_index('bleach', create_book_schema(), cls.book_idx_dir)
		cls.bim = WhooshBookIndexManager('bleach', 'bleach', indexdir=cls.book_idx_dir)

		idx = cls.bim.bookidx
		writer = idx.writer()
		for k, x in enumerate(phrases):
			writer.add_document(ntiid = unicode(make_ntiid(provider=str(k), nttype='bleach', specific='manga')),
								title = unicode(x),
								content = unicode(x),
								quick = unicode(x),
								related= u'',
								last_modified=datetime.fromtimestamp(cls.now))
		writer.commit()

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.book_idx_dir, True)
		super(_BaseIndexManagerTest,cls).tearDownClass()

	def wait_delay(self):
		pass

	@WithMockDSTrans
	def test_add_book(self):
		self.im = self.create_index_mananger()
		assert_that(self.im.add_book(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir), is_(True))
		assert_that(self.im.add_book(indexname='unknown', ntiid='unknown', indexdir='/tmp'), is_(False))

	@WithMockDSTrans
	def test_search_book(self):
		self.im = self.create_index_mananger()
		self.im.add_book(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(indexid='bleach', query='omega')
		hits = self.im.content_search(query=q)
		assert_that(hits, has_length(1))

		q = QueryObject(indexid='bleach', query='wen')
		hits = self.im.content_suggest_and_search(query=q)
		assert_that(hits, has_length(1))

		q = QueryObject(indexid='bleach', query='extre')
		hits = self.im.content_suggest(query=q)
		assert_that(hits, has_length(1))

	def _add_notes_to_ds(self, strings=zanpakuto_commands):
		notes = []
		conn = mock_dataserver.current_transaction

		username = str(uuid.uuid4()).split('-')[-1] + '@nti.com'
		usr = User.create_user( mock_dataserver.current_mock_ds, username=username, password='temp001' )

		for x in strings:
			note = Note()
			note.body = [unicode(x)]
			note.creator = usr.username
			note.containerId = make_ntiid(nttype='bleach', specific='manga')
			conn.add(note)
			notes.append(usr.addContainedObject( note ))
		return notes, usr

	def _add_notes_to_index(self, im, notes, user):
		for note in notes:
			im.index_user_content(data=note, target=user)
		return notes

	def _add_notes_and_index(self, strings=zanpakuto_commands):
		self.im = self.create_index_mananger()
		notes, usr = self._add_notes_to_ds(strings)
		self._add_notes_to_index(self.im, notes, usr)
		return notes, usr

	@WithMockDSTrans
	def test_unified_search(self):
		_, usr = self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir)
		self.wait_delay()

		q = QueryObject(term='omega', indexid='bleach', username=usr.username)
		hits = self.im.search(q)
		assert_that(hits, has_length(2))

		q.term = 'coffee'
		hits = self.im.search(q)
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_unified_search_ngrams(self):
		_, usr = self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', indexdir=self.book_idx_dir)
		self.wait_delay()

		q = QueryObject(term='omeg', indexid='bleach', username=usr.username)
		hits = self.im.suggest(q)
		assert_that(hits, has_length(1))

		hits = self.im.suggest_and_search(q)
		assert_that(hits, has_length(2))

	@WithMockDSTrans
	def test_unified_search_suggest(self):
		_, usr = self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', indexdir=self.book_idx_dir)
		self.wait_delay()

		q = QueryObject(term='omeg', indexid='bleach', username=usr.username)
		hits = self.im.suggest(q)
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_unified_search_suggest_and_search(self):
		_, usr = self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', indexdir=self.book_idx_dir)
		self.wait_delay()

		q = QueryObject(term='omeg', indexid='bleach', username=usr.username)
		hits = self.im.suggest_and_search(q)
		assert_that(hits, has_length(2))

	@WithMockDSTrans
	def test_add_notes(self):
		self._add_notes_and_index()

	@WithMockDSTrans
	def test_search_notes(self):
		_, usr = self._add_notes_and_index()
		self.wait_delay()

		q = QueryObject(term='not_to_be_found', username=usr.username, searchon=('Notes',))
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(0))

		q = QueryObject(term='rage', username=usr.username, searchon=('Notes',))
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_search_notes_suggest(self):
		_, usr = self._add_notes_and_index()
		self.wait_delay()

		q = QueryObject(term='flow', username=usr.username, searchon=('Notes',))
		hits = self.im.user_data_suggest(q)
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_search_notes_suggest_and_search(self):
		_, usr = self._add_notes_and_index()
		self.wait_delay()

		q = QueryObject(term='creat', username=usr.username, searchon=('Notes',))
		hits = self.im.user_data_suggest_and_search(query=q)
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_update_delete_note(self):
		notes, user = self._add_notes_and_index()
		self.wait_delay()

		note = notes[0]
		note.body = [u'Shoot To Death']
		self.im.update_user_content(user, data=note)
		q = QueryObject(term='death', username=user.username, searchon=('Notes',))
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(2))

		note = notes[1]
		self.im.delete_user_content(user, data=note)
		q = QueryObject(term='deviate', username=user.username, searchon=('Notes',))
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(0))

	@WithMockDSTrans
	def test_note_share_comm(self):
		ds = mock_dataserver.current_mock_ds
		user_1 = User.create_user( ds, username='nti-1.com', password='temp001')
		user_2 = User.create_user( ds, username='nti-2.com', password='temp001')

		c = Community.create_community( ds, username='Bankai')
		for u in (user_1, user_2):
			u.record_dynamic_membership( c )
			u.follow( c )

		note = Note()
		note.body = [unicode('Hitsugaya and Madarame performing Jinzen')]
		note.creator = 'nti.com'
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		note.addSharingTarget( c )
		note = user_2.addContainedObject( note )

		self.im = self.create_index_mananger()
		self.im.index_user_content(data=note, target=user_2)
		self.im.index_user_content(data=note, target=c)
		self.wait_delay()

		q = QueryObject(term='jinzen', username=user_1.username)
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_same_content_two_comm(self):
		ds = mock_dataserver.current_mock_ds
		user = User.create_user( ds, username='nti.com', password='temp001')

		note = Note()
		note.body = [unicode('Only a few atain both')]
		note.creator = 'nti.com'
		note.containerId = make_ntiid(nttype='bleach', specific='manga')

		comms = []
		for name in ('Bankai', 'Shikai'):
			c = Community.create_community( ds, username=name)
			user.record_dynamic_membership( c )
			user.follow( c )
			comms.append(c)
			note.addSharingTarget( c )

		note = user.addContainedObject( note )

		self.im = self.create_index_mananger()
		for c in comms:
			self.im.index_user_content(data=note, target=c)
		self.wait_delay()

		q = QueryObject(term='atain', username=user.username)
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(2))

		hits = toExternalObject(hits)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(ITEMS, has_length(1)))

	@WithMockDSTrans
	def test_note_share_dfl(self):
		ds = mock_dataserver.current_mock_ds
		ichigo = User.create_user( ds, username='ichigo@nti.com', password='temp001')
		aizen = User.create_user( ds, username='aizen@nti.com', password='temp001')
		gin = User.create_user( ds, username='gin@nti.com', password='temp001')

		bleach = DynamicFriendsList(username='bleach')
		bleach.creator = ichigo # Creator must be set
		ichigo.addContainedObject( bleach )
		bleach.addFriend( aizen )
		bleach.addFriend( gin )

		note = Note()
		note.body = [u'Getsuga Tensho']
		note.creator = 'nti.com'
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		note.addSharingTarget( bleach )
		note = ichigo.addContainedObject( note )

		self.im = self.create_index_mananger()
		for c in (ichigo, bleach):
			self.im.index_user_content(data=note, target=c)

		q = QueryObject(term='getsuga', username=gin.username)
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(1))

		q = QueryObject(term='tensho', username=aizen.username)
		hits = self.im.user_data_search(query=q)
		assert_that(hits, has_length(1))

class TestIndexManagerWithRepoze(_BaseIndexManagerTest):

	def create_index_mananger(self):
		return create_index_manager_with_repoze()

class TestIndexManagerWithWhoosh(_BaseIndexManagerTest):

	@classmethod
	def setUpClass(cls):
		cls.whoosh_dir = tempfile.mkdtemp(dir="/tmp")
		os.environ['DATASERVER_DIR']= cls.whoosh_dir
		# Yes, this is backwards, but order matters: the factory won't install
		# the storage if DATASERVER_DIR is not set (which is weird)
		super(TestIndexManagerWithWhoosh,cls).setUpClass()

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.whoosh_dir, True)
		super(TestIndexManagerWithWhoosh,cls).tearDownClass()

	def create_index_mananger(self):
		return create_index_manager_with_whoosh(indexdir=self.whoosh_dir, use_md5=False)
