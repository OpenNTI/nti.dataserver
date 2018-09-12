#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
does_not = is_not

import unittest

import fudge

from zope import interface

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

from nti.base.interfaces import INamedFile


class TestMixins(unittest.TestCase):

    @fudge.patch('nti.app.contentfile.view_mixins.find_object_with_ntiid')
    def test_get_file_from_oid_external_link(self, mock_fon):

        class Foo(object):
            pass
        foo = Foo()
        interface.alsoProvides(foo, INamedFile)
        mock_fon.is_callable().with_args().returns(foo)

        href = '/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_(foo))

        href = '/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_(foo))

        href = '/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/download'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_(foo))

        href = '/dataserver2/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/download/foo.dat'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_(foo))

        href = '/dataserver2/Objects/xxx'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_(none()))

        href = 'http://x.org/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_not(none()))

        href = 'http://x.org/Objects/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_not(none()))

        href = '/dataserver2/Objects/tag%3Anextthought.com%2C2011-10%3Azope.security.management.system_user-OID-0x3fb1a3e4dc1691ea%3A5573657273%3Atux9jJFntYr/download/ichigo.xml'
        assert_that(get_file_from_oid_external_link(href),
                    is_(foo))

        href = '/dataserver2/Objects/tag%3Anextthought.com%2C2011-10%3Azope.security.management.system_user-OID-0x3fb1a3e4dc1691ea%3A5573657273%3Atux9jJFntYr'
        assert_that(get_file_from_oid_external_link(href),
                    is_(foo))

        interface.noLongerProvides(foo, INamedFile)
        href = 'http://x.org/tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2015_CS_1323/@@view'
        n = get_file_from_oid_external_link(href)
        assert_that(n, is_(none()))

        href = '/dataserver2/Objects/tag%3Anextthought.com%2C2011-10%3Azope.security.management.system_user-OID-0x3fb1a3e4dc1691ea%3A5573657273%3Atux9jJFntYr/download/ichigo.xml'
        assert_that(is_oid_external_link(href),
                    is_(True))
