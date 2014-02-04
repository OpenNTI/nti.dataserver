#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

import os
import time
import shutil
import tempfile
from datetime import datetime

from whoosh.filedb.filestore import RamStorage

from nti.dataserver.users import User
from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from ..whoosh_index import Book

from ..constants import (HIT_COUNT, ITEMS)

import nti.dataserver.tests.mock_dataserver as mock_dataserver

from . import zanpakuto_commands
from . import ConfiguringTestBase

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
			assert_that(d, has_entry('Query', 'shield'))
			assert_that(d, has_key(ITEMS))
			items = d[ITEMS]
			assert_that(items, has_length(1))
