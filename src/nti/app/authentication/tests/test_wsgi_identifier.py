#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import fudge
import unittest

from repoze.who.interfaces import IAPIFactory

from nti.app.authentication.interfaces import ILogonWhitelist

from nti.app.authentication.who_apifactory import create_who_apifactory

from nti.app.authentication.wsgi_identifier import identify_handler_factory

from nti.appserver.interfaces import IApplicationSettings


class TestWsgiIdentifier(unittest.TestCase):

    @fudge.patch('zope.component.getUtility')
    def test_classification_through_api(self, mock_get):
        apifactory = None
        whitelist = []

        def getUtility(iface):
            if iface == IApplicationSettings:
                return {}
            if iface == IAPIFactory:
                return apifactory
            assert iface == ILogonWhitelist
            return whitelist

        mock_get.is_callable().calls(getUtility)

        apifactory = create_who_apifactory()

        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'localhost', 'SERVER_PORT': '80',
                   'REQUEST_METHOD': 'GET'}

        handler = identify_handler_factory(lambda e, s:  42)

        # First, a different path
        environ['PATH_INFO'] = '/to_the_app'
        assert_that(handler(environ, None), is_(42))

        # ok, now the real path, without a cookie
        environ['PATH_INFO'] = '/_ops/identify'

        called = []
        assert_that(handler(environ,
                            lambda s, h: called.append((s, h))),
                    is_(("",)))
        assert_that(called[0],
                    is_(('403 Forbidden', [('Content-Type', 'text/plain')])))
        del called[:]

        # Now pretend we have an auth cookie
        api = apifactory(environ)
        auth_tkt = api.name_registry[apifactory.default_identifier_name]

        cookie = auth_tkt.remember(environ, {'repoze.who.userid': 'jason'})[0]
        environ['HTTP_COOKIE'] = cookie[1]
        del environ['paste.cookies']

        # but we're not in the whitelist
        assert_that(handler(environ,
                            lambda s, h: called.append((s, h))),
                    is_(("",)))
        assert_that(called[0],
                    is_(('403 Forbidden', [('Content-Type', 'text/plain')])))
        del called[:]

        whitelist.append('jason')
        assert_that(handler(environ,
                            lambda s, h: called.append((s, h))),
                    is_(("",)))
        assert_that(called[0],
                    is_(('200 OK', [('Content-Type', 'text/plain')])))
