#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_entry
from hamcrest import assert_that

import fudge
import unittest

from nti.app.authentication.user_token import DefaultIdentifiedUserTokenAuthenticator

from nti.app.authentication.who_authenticators import KnownUrlTokenBasedAuthenticator

class TestKnownUrlTokenBasedAuthenticator(unittest.TestCase):

	def setUp(self):
		self.plugin = KnownUrlTokenBasedAuthenticator('secret', allowed_views=('feed.atom', 'test'))

	def test_identify_empty_environ(self):
		assert_that(self.plugin.identify({}), is_(none()))
		assert_that(self.plugin.identify({'QUERY_STRING': ''}), is_(none()))

		assert_that(self.plugin.identify({'QUERY_STRING': 'token=foo'}),
					is_(none()))

	def test_identify_wrong_view(self):
		assert_that(self.plugin.identify({'QUERY_STRING': 'token',
											'PATH_INFO': '/foo/bar'}),
					is_(none()))

	@fudge.patch('nti.app.authentication.user_token.DefaultIdentifiedUserTokenAuthenticator._get_user_password',
				 'zope.component.getAdapter')
	def test_identify_token(self, mock_pwd, mock_get):
		mock_pwd.is_callable().returns_fake().provides('getPassword').returns('abcde')
		tokens = DefaultIdentifiedUserTokenAuthenticator('secret')
		mock_get.is_callable().returns(tokens)

		token = tokens.getTokenForUserId('user')
		environ = {'QUERY_STRING': 'token=' + token,
				   'PATH_INFO': '/feed.atom'}

		identity = self.plugin.identify(environ)
		assert_that(self.plugin.authenticate(environ, identity),
					is_('user'))

		# Password change behind the scenes
		mock_pwd.is_callable().returns_fake().provides('getPassword').returns('1234')
		assert_that(self.plugin.authenticate(environ, identity),
					is_(none()))

		# Back to original
		mock_pwd.is_callable().returns_fake().provides('getPassword').returns('abcde')
		identity = self.plugin.identify(environ)
		assert_that(self.plugin.authenticate(environ, identity),
					is_('user'))
