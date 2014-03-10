#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import is_not as does_not

import fudge

from pyramid.httpexceptions import HTTPFound

from ..who_redirector import BrowserRedirectorPlugin
from ..who_apifactory import create_who_apifactory

class TestWhoRedirector(unittest.TestCase):

	def test_redirect(self):
		plugin = BrowserRedirectorPlugin(str('/login'),
										 came_from_param=str('return'))
		exc = plugin.challenge({ b'wsgi.url_scheme': 'http',
								 b'SERVER_NAME': 'localhost', b'SERVER_PORT': '80'},
							   401, [], [])

		assert_that( exc, is_(HTTPFound) )
		assert_that( exc.headers, has_length(3) )
		del exc.headers['Content-Length']
		del exc.headers['Content-Type']
		assert_that( exc.headers, has_length(1) )
		assert_that( exc.headers['Location'], is_('/login?return=http%3A%2F%2Flocalhost%2F'))

	@fudge.patch('zope.component.getUtility')
	def test_classification_through_api(self, mock_get):
		mock_get.is_callable().returns({'login_app_root': '/login'})

		apifactory = create_who_apifactory()

		environ = { b'wsgi.url_scheme': 'http',
					b'SERVER_NAME': 'localhost', b'SERVER_PORT': '80',
					b'REQUEST_METHOD': b'GET'}
		api = apifactory(environ)
		api.classification = 'browser'

		# as a browser, we get the redirect
		exc = api.challenge(app_headers=[])
		assert_that( exc, is_(HTTPFound) )
		assert_that( exc.headers, has_length(3) )
		del exc.headers['Content-Length']
		del exc.headers['Content-Type']
		assert_that( exc.headers, has_length(1) )
		assert_that( exc.headers['Location'], is_('/login?return=http%3A%2F%2Flocalhost%2F'))

		# as an app, we get something without the www-authenticate header
		api.classification = 'application-browser'
		exc = api.challenge(app_headers=[])
		assert_that( exc.headers, does_not( has_key('WWW-Authenticate' )))

		api.classification = 'other'
		exc = api.challenge(app_headers=[])
		assert_that( exc.headers, has_key('WWW-Authenticate' ))
