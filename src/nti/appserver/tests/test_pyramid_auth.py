#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import has_key
from hamcrest import none

from nti.testing.matchers import validly_provides

from nti.appserver.pyramid_auth import _NonChallengingBasicAuthPlugin
from nti.appserver.pyramid_auth import _nti_request_classifier
from nti.appserver.pyramid_auth import CLASS_BROWSER_APP
from repoze.who.interfaces import IChallenger, IRequestClassifier

import unittest

class TestMisc(unittest.TestCase):

	def test_non_challenging_challenge(self):

		challenger = _NonChallengingBasicAuthPlugin('nti')
		assert_that( challenger, validly_provides(IChallenger) )

		# Challenging produces as 401, but without a WWW-Authenticate header
		unauth = challenger.challenge( {}, '401', {}, [] )
		assert_that( unauth.headers, does_not( has_key( 'WWW-Authenticate' ) ) )
		assert_that( unauth.headers, has_key( 'Content-Type' ) )

		# forgetting adds no headers
		assert_that( challenger.forget( {}, {} ), is_( () ) )

	def test_request_classifier(self):

		assert_that( _nti_request_classifier, validly_provides(IRequestClassifier) )

		# The default
		environ = {}
		environ['REQUEST_METHOD'] = 'GET'

		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		# XHR
		environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
		assert_that( _nti_request_classifier( environ ),
					 is_( CLASS_BROWSER_APP ) )
		environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'.upper() # case-insensitive
		assert_that( _nti_request_classifier( environ ),
					 is_( CLASS_BROWSER_APP ) )

		del environ['HTTP_X_REQUESTED_WITH']

		environ['HTTP_REFERER'] = 'http://foo'

		# A referrer alone isn't enough
		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		# Add  a user agent
		environ['HTTP_USER_AGENT'] = 'Mozilla'
		__traceback_info__ = environ
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )

		# But a default accept changes back to browser
		environ['HTTP_ACCEPT'] = '*/*'
		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		environ['HTTP_ACCEPT'] = 'text/plain'
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )


from ..pyramid_auth import _KnownUrlTokenBasedAuthenticator
from nti.app.authentication.user_token import DefaultIdentifiedUserTokenAuthenticator
import fudge
class TestKnownUrlTokenBasedAuthenticator(unittest.TestCase):

	def setUp(self):
		self.plugin = _KnownUrlTokenBasedAuthenticator('secret', allowed_views=('feed.atom','test') )

	def test_identify_empty_environ(self):
		assert_that( self.plugin.identify( {} ), is_( none() ) )
		assert_that( self.plugin.identify( {'QUERY_STRING': ''} ), is_( none() ) )

		assert_that( self.plugin.identify( {'QUERY_STRING': 'token=foo'} ),
					 is_( none() ) )

	def test_identify_wrong_view(self):
		assert_that( self.plugin.identify( {'QUERY_STRING': 'token',
											'PATH_INFO': '/foo/bar'} ),
					 is_( none() ) )

	@fudge.patch('nti.app.authentication.user_token.DefaultIdentifiedUserTokenAuthenticator._get_user_password',
				 'zope.component.getAdapter')
	def test_identify_token(self, mock_pwd, mock_get):
		mock_pwd.is_callable().returns_fake().provides( 'getPassword' ).returns( 'abcde' )
		mock_get.is_callable().returns(DefaultIdentifiedUserTokenAuthenticator('secret'))

		token = self.plugin.getTokenForUserId( 'user' )
		environ = {'QUERY_STRING': 'token=' + token,
				   'PATH_INFO': '/feed.atom'}

		identity = self.plugin.identify( environ )
		assert_that( self.plugin.authenticate( environ, identity ),
					 is_( 'user' ) )

		# Password change behind the scenes
		mock_pwd.is_callable().returns_fake().provides( 'getPassword' ).returns( '1234' )
		assert_that( self.plugin.authenticate( environ, identity ),
					 is_( none() ) )

		# Back to original
		mock_pwd.is_callable().returns_fake().provides( 'getPassword' ).returns( 'abcde' )
		identity = self.plugin.identify( environ )
		assert_that( self.plugin.authenticate( environ, identity ),
					 is_( 'user' ) )
