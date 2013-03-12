#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from datetime import datetime

from ..common import epoch_time
from ..common import get_datetime

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, less_than_or_equal_to)

class TestCommon(ConfiguringTestBase):

	def test_epoch_time(self):
		d = datetime.fromordinal(730920)
		assert_that(epoch_time(d), is_(1015826400.0) )
		assert_that(epoch_time(None), is_(0))

	def test_get_datetime(self):
		f = 1321391468.411328
		s = '1321391468.411328'
		assert_that(get_datetime(f), is_(get_datetime(s)))
		assert_that(datetime.now(), less_than_or_equal_to(get_datetime()))
