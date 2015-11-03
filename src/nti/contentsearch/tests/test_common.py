#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_entry
from hamcrest import assert_that

import unittest
from datetime import datetime

from ..common import epoch_time
from ..common import is_all_query
from ..common import get_mime_type_map
from ..common import get_type_from_mimetype

from . import SharedConfiguringTestLayer

class TestCommon(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_all_query(self):
		assert_that(is_all_query('?'), is_(True))
		assert_that(is_all_query('*'), is_(True))
		assert_that(is_all_query('?x'), is_(True))
		assert_that(is_all_query('*x'), is_(True))
		assert_that(is_all_query('x*'), is_(False))
		assert_that(is_all_query('xxx'), is_(False))

	def test_epoch_time(self):
		d = datetime.fromordinal(730920)
		assert_that(epoch_time(d), is_(1015826400.0))
		assert_that(epoch_time(None), is_(0))

	def test_get_mime_type_map(self):
		mmap = get_mime_type_map()
		assert_that(mmap, has_entry('application/vnd.nextthought.redaction', 'redaction'))
		assert_that(mmap, has_entry('application/vnd.nextthought.forums.post', 'post'))
		assert_that(mmap, has_entry('application/vnd.nextthought.highlight', 'highlight'))
		assert_that(mmap, has_entry('application/vnd.nextthought.note', 'note'))
		assert_that(mmap, has_entry('application/vnd.nextthought.messageinfo', 'messageinfo'))
		assert_that(mmap, has_entry('application/vnd.nextthought.bookcontent', 'content'))
		assert_that(mmap, has_entry('application/vnd.nextthought.nticard', 'nticard'))
		assert_that(mmap, has_entry('application/vnd.nextthought.videotranscript', 'videotranscript'))
		assert_that(mmap, has_entry('application/vnd.nextthought.forums.personalblogentrypost', 'post'))
		assert_that(mmap, has_entry('application/vnd.nextthought.forums.personalblogcomment', 'comment'))
		assert_that(mmap, has_entry('application/vnd.nextthought.forums.generalforum', 'forum'))
		assert_that(mmap, has_entry('application/vnd.nextthought.forums.communityforum', 'forum'))

	def test_get_type_from_mimetype(self):
		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.generalforum'), is_('forum'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.communityforum'), is_('forum'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.personalblogentrypost'), is_('post'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.personalblogcomment'), is_('comment'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.post'), is_('post'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.post'), is_('post'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.content'), is_('content'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.redaction'), is_('redaction'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.highlight'), is_('highlight'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.note'), is_('note'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.transcript'), is_('messageinfo'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.messageinfo'), is_('messageinfo'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.nticard'), is_('nticard'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.videotranscript'), is_('videotranscript'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.xyz'), is_(none()))
		assert_that(get_type_from_mimetype('foo'), is_(none()))
		assert_that(get_type_from_mimetype(None), is_(none()))
