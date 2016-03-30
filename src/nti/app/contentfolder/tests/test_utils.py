#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
does_not = is_not

import fudge
import unittest

from zope import interface

from plone.namedfile.interfaces import INamed

from nti.app.contentfolder.utils import get_file_from_cf_io_url

class TestUtils(unittest.TestCase):

	@fudge.patch('nti.app.contentfolder.utils.get_object')
	def test_get_file_from_cf_io_url(self, mock_fon):
		class Foo(object):
			pass
		foo = Foo()
		interface.alsoProvides(foo, INamed)
		mock_fon.is_callable().with_args().returns(foo)

		n = get_file_from_cf_io_url('/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323')
		assert_that(n, is_(none()))

		n = get_file_from_cf_io_url('/dataserver2/cf.io/xrPH9')
		assert_that(n, is_(foo))

		n = get_file_from_cf_io_url('/dataserver2/cf.io/xrPH9/sample.dat')
		assert_that(n, is_(foo))

