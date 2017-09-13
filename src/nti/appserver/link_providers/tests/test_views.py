#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_item
from hamcrest import assert_that

from zope import interface

from zope.component.hooks import site

from pyramid.request import Request

from nti.appserver.httpexceptions import HTTPSeeOther
from nti.appserver.httpexceptions import HTTPNotFound
from nti.appserver.httpexceptions import HTTPNoContent

from nti.appserver.link_providers.views import named_link_get_view
from nti.appserver.link_providers.views import named_link_delete_view

from nti.appserver.policies.sites import BASECOPPA as MATHCOUNTS

from nti.site.transient import TrivialSite as _TrivialSite

from nti.dataserver.interfaces import ICoppaUser

from nti.dataserver.users.users import User

from nti.appserver.link_providers.tests.test_zcml import ZCML_STRING

import nti.testing.base


class TestViews(nti.testing.base.ConfiguringTestBase):

    def setUp(self):
        super(TestViews, self).setUp()
        self.configure_string(ZCML_STRING)
        self.user = User(u'foo@bar')
        self.request = Request.blank('/')
        self.request.subpath = ()
        self.request.context = self.user

    def _test_common(self, view):
        request = self.request
        # no subpath
        assert_that(view(request), is_(HTTPNotFound))

        # wrong subpath
        request.subpath = ('unregistered',)
        assert_that(view(request), is_(HTTPNotFound))

        # right subpath, wrong user type
        request.subpath = ('foo.bar',)
        assert_that(view(request), is_(HTTPNotFound))

    def test_get_view(self):
        with site(_TrivialSite(MATHCOUNTS)):
            self._test_common(named_link_get_view)

            # finally the stars align
            interface.alsoProvides(self.user, ICoppaUser)
            result = named_link_get_view(self.request)
            assert_that(result, is_(HTTPSeeOther))
            assert_that(result.location, is_('/relative/path'))
            # made absolute on output
            headerlist = []

            def start_request(unused_status, headers):
                headerlist.extend(headers)
            result(self.request.environ, start_request)
            assert_that(headerlist,
                        has_item(('Location', 'http://localhost/relative/path')))

    def test_get_view_wrong_site(self):
        self._test_common(named_link_get_view)

        interface.alsoProvides(self.user, ICoppaUser)
        assert_that(named_link_get_view(self.request), is_(HTTPNotFound))

    def test_delete_view(self):
        with site(_TrivialSite(MATHCOUNTS)):
            self._test_common(named_link_delete_view)

            # finally the stars align
            interface.alsoProvides(self.user, ICoppaUser)
            assert_that(named_link_delete_view(self.request), 
                        is_(HTTPNoContent))

            # Doing it again is not found
            assert_that(named_link_delete_view(self.request), 
                        is_(HTTPNotFound))

            # As is a get
            assert_that(named_link_get_view(self.request), 
                        is_(HTTPNotFound))
