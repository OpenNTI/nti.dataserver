#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

# from zope import component
from datetime import datetime

from ..common import epoch_time
from ..common import get_datetime
from ..common import get_type_from_mimetype

# from nti.externalization.interfaces import IMimeObjectFactory

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, less_than_or_equal_to, none)

class TestCommon(ConfiguringTestBase):

	def test_epoch_time(self):
		d = datetime.fromordinal(730920)
		assert_that(epoch_time(d), is_(1015826400.0))
		assert_that(epoch_time(None), is_(0))

	def test_get_datetime(self):
		f = 1321391468.411328
		s = '1321391468.411328'
		assert_that(get_datetime(f), is_(get_datetime(s)))
		assert_that(datetime.now(), less_than_or_equal_to(get_datetime()))

	def test_get_type_from_mimetype(self):

# 		f = component.getUtilitiesFor(IMimeObjectFactory)
# 		for name, utility in f:
# 			i = utility.getInterfaces()
# 			for k in i._implied.keys():
# 				print(type(k), getattr(i, '__name__', None))
# 			print(name, getattr(i, '__name__', None))

		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.personalblogentrypost'), is_('post'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.forums.personalblogcomment'), is_('post'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.post'), is_('post'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.content'), is_('content'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.redaction'), is_('redaction'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.highlight'), is_('highlight'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.note'), is_('note'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.transcript'), is_('messageinfo'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.messageinfo'), is_('messageinfo'))
		assert_that(get_type_from_mimetype('application/vnd.nextthought.xyz'), is_(none()))
		assert_that(get_type_from_mimetype('foo'), is_(none()))
		assert_that(get_type_from_mimetype(None), is_(none()))
