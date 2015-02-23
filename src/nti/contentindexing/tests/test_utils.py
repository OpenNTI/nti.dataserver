#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import less_than_or_equal_to

import unittest
from datetime import datetime

from nti.contentindexing.utils import get_datetime
from nti.contentindexing.utils import date_to_videotimestamp

from nti.contentindexing.tests import SharedConfiguringTestLayer

class TestUtils(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_videotimestamp_to_text(self):
        f = 1321391468.413528
        assert_that(date_to_videotimestamp(f), is_('15:11:08.413'))
        assert_that(date_to_videotimestamp(str(f)), is_('15:11:08.410'))
        assert_that(date_to_videotimestamp(None), is_(u''))

    def test_get_datetime(self):
        f = 1321391468.411328
        s = '1321391468.411328'
        assert_that(get_datetime(f), is_(get_datetime(s)))
        assert_that(datetime.now(), less_than_or_equal_to(get_datetime()))
