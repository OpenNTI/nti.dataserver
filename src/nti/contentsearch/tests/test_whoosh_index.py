#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import time
import shutil
import tempfile
from datetime import datetime

from whoosh.filedb.filestore import RamStorage

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note as dsNote
from nti.dataserver.contenttypes import Highlight as dsHighlight
from nti.dataserver.contenttypes import Redaction as dsRedaction

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object

from .._whoosh_index import Note
from .._whoosh_index import Book
from .._whoosh_index import Highlight
from .._whoosh_index import Redaction

from ..constants import (HIT_COUNT, QUERY, ITEMS)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import zanpakuto_commands
from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_entry, has_key, has_length)

class TestWhooshIndex(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestWhooshIndex, cls).setUpClass()
		cls.db_dir = tempfile.mkdtemp(dir="/tmp")
		os.environ['DATASERVER_DIR'] = cls.db_dir

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.db_dir, True)
		super(TestWhooshIndex, cls).tearDownClass()

	def _create_user(self, ds=None, username='nt@nti.com', password='temp001'):
		ds = ds or mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	def _create_ds_note(self):
		username = 'nt@nti.com'
		usr = self._create_user(username=username)
		note = dsNote()
		note.creator = username
		note.body = [u'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade']
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject(note)
		return note

	@WithMockDSTrans
	def test_index_note(self):
		note = Note()
		schema = note.schema
		idx = RamStorage().create_index(schema)
		note.index_content(idx.writer(), self._create_ds_note())
		with idx.searcher() as s:
			assert_that(s.doc_count(), is_(1))
			d = toExternalObject(note.search(s, "rise"))
			assert_that(d, has_entry(HIT_COUNT, 1))
			assert_that(d, has_entry(QUERY, 'rise'))
			assert_that(d, has_key(ITEMS))
			items = d[ITEMS]
			assert_that(items, has_length(1))

	def _create_ds_highlight(self):
		username = 'nt@nti.com'
		usr = self._create_user(username=username)
		highlight = dsHighlight()
		highlight.selectedText = u'You know how to add, subtract, multiply, and divide'
		highlight.creator = usr.username
		highlight.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(highlight)
		highlight = usr.addContainedObject(highlight)
		return highlight

	@WithMockDSTrans
	def test_index_highlight(self):
		hi = Highlight()
		schema = hi.schema
		idx = RamStorage().create_index(schema)
		hi.index_content(idx.writer(), self._create_ds_highlight())
		with idx.searcher() as s:
			assert_that(s.doc_count(), is_(1))
			d = toExternalObject(hi.search(s, "divide"))
			assert_that(d, has_entry(HIT_COUNT, 1))
			assert_that(d, has_entry(QUERY, 'divide'))
			assert_that(d, has_key(ITEMS))

	def _create_ds_redaction(self):
		usr = self._create_user()
		redaction = dsRedaction()
		redaction.selectedText = u'Lord of Winterfell'
		update_from_external_object(redaction, {'replacementContent': u'Game of Thrones',
												'redactionExplanation': u'Eddard Stark'})
		redaction.creator = usr.username
		redaction.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(redaction)
		redaction = usr.addContainedObject(redaction)
		return redaction

	@WithMockDSTrans
	def test_index_redaction(self):
		rd = Redaction()
		schema = rd.schema
		idx = RamStorage().create_index(schema)
		rd.index_content(idx.writer(), self._create_ds_redaction())
		with idx.searcher() as s:
			assert_that(s.doc_count(), is_(1))
			d = toExternalObject(rd.search(s, "stark"))
			assert_that(d, has_entry(HIT_COUNT, 1))
			assert_that(d, has_entry(QUERY, 'stark'))
			assert_that(d, has_key(ITEMS))

	def test_whoosh_book(self):
		bk = Book()
		now = time.time()
		schema = bk.schema
		idx = RamStorage().create_index(schema)
		writer = idx.writer()
		for x in zanpakuto_commands:
			writer.add_document(ntiid=unicode(make_ntiid(nttype='bleach', specific='manga')),
								title=unicode(x),
								content=unicode(x),
								quick=unicode(x),
								related=u'',
								last_modified=datetime.fromtimestamp(now))
		writer.commit()

		with idx.searcher() as s:
			d = toExternalObject(bk.search(s, "shield"))
			assert_that(d, has_entry(HIT_COUNT, 1))
			assert_that(d, has_entry(QUERY, 'shield'))
			assert_that(d, has_key(ITEMS))
			items = d[ITEMS]
			assert_that(items, has_length(1))
