#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import is_not as does_not

import unittest

import fudge

from pyramid.httpexceptions import HTTPFound

from nti.app.authentication.who_apifactory import create_who_apifactory
from nti.app.authentication.who_redirector import BrowserRedirectorPlugin


class TestWhoRedirector(unittest.TestCase):

    def test_redirect(self):
        plugin = BrowserRedirectorPlugin(str('/login'),
                                         came_from_param=str('return'))
        exc = plugin.challenge({'wsgi.url_scheme': 'http',
                                'SERVER_NAME': 'localhost', 'SERVER_PORT': '80'},
                               401, [], [])

        assert_that(exc, is_(HTTPFound))
        assert_that(exc.headers, has_length(3))
        del exc.headers['Content-Length']
        del exc.headers['Content-Type']
        assert_that(exc.headers, has_length(1))
        assert_that(exc.headers['Location'], 
					is_('/login?return=http%3A%2F%2Flocalhost%2F'))

    @fudge.patch('zope.component.getUtility')
    def test_classification_through_api(self, mock_get):
        mock_get.is_callable().returns({'login_app_root': '/login'})

        apifactory = create_who_apifactory()

        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'localhost', 'SERVER_PORT': '80',
                   'REQUEST_METHOD': 'GET'}
        api = apifactory(environ)
        api.classification = 'browser'

        # as a browser, we get the redirect
        exc = api.challenge(app_headers=[])
        assert_that(exc, is_(HTTPFound))
        assert_that(exc.headers, has_length(3))
        del exc.headers['Content-Length']
        del exc.headers['Content-Type']
        assert_that(exc.headers, has_length(1))
        assert_that(exc.headers['Location'], 
					is_('/login?return=http%3A%2F%2Flocalhost%2F'))

        # as an app, we get something without the www-authenticate header
        api.classification = 'application-browser'
        exc = api.challenge(app_headers=[])
        assert_that(exc.headers, does_not(has_key('WWW-Authenticate')))

        api.classification = 'other'
        exc = api.challenge(app_headers=[])
        assert_that(exc.headers, has_key('WWW-Authenticate'))
