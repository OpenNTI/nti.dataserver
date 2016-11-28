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

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

class TestMixins(unittest.TestCase):

	@fudge.patch('nti.app.contentfile.view_mixins.find_object_with_ntiid')
	def test_get_file_from_oid_external_link(self, mock_fon):
		class Foo(object):
			pass
		foo = Foo()
		interface.alsoProvides(foo, INamed)
		mock_fon.is_callable().with_args().returns(foo)

		n = get_file_from_oid_external_link('/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323')
		assert_that(n, is_(foo))

		n = get_file_from_oid_external_link('/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view')
		assert_that(n, is_(foo))

		n = get_file_from_oid_external_link('/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/download')
		assert_that(n, is_(foo))

		n = get_file_from_oid_external_link('/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/download/foo.dat')
		assert_that(n, is_(foo))

		n = get_file_from_oid_external_link('/dataserver2/Objects/xxx')
		assert_that(n, is_(none()))

		n = get_file_from_oid_external_link('http://x.org/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view')
		assert_that(n, is_not(none()))

		n = get_file_from_oid_external_link('http://x.org/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view')
		assert_that(n, is_not(none()))

		assert_that(get_file_from_oid_external_link(
						'/dataserver2/Objects/tag%3Anextthought.com%2C2011-10%3Azope.security.management.system_user-OID-0x3fb1a3e4dc1691ea%3A5573657273%3Atux9jJFntYr/download/ichigo.xml'),
					is_(foo))

		assert_that(get_file_from_oid_external_link(
						'/dataserver2/Objects/tag%3Anextthought.com%2C2011-10%3Azope.security.management.system_user-OID-0x3fb1a3e4dc1691ea%3A5573657273%3Atux9jJFntYr'),
					is_(foo))

		interface.noLongerProvides(foo, INamed)
		n = get_file_from_oid_external_link('http://x.org/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view')
		assert_that(n, is_(none()))

		assert_that(is_oid_external_link(
						'/dataserver2/Objects/tag%3Anextthought.com%2C2011-10%3Azope.security.management.system_user-OID-0x3fb1a3e4dc1691ea%3A5573657273%3Atux9jJFntYr/download/ichigo.xml'),
					is_(True))
