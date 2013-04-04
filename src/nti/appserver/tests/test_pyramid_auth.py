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

from nti.tests import validly_provides

from pyramid.request import Request

from nti.appserver.pyramid_auth import _decode_username_request
from nti.appserver.pyramid_auth import _NonChallengingBasicAuthPlugin
from nti.appserver.pyramid_auth import _nti_request_classifier
from nti.appserver.pyramid_auth import CLASS_BROWSER_APP
from repoze.who.interfaces import IChallenger, IRequestClassifier

def test_non_challenging_challenge():

	challenger = _NonChallengingBasicAuthPlugin('nti')
	assert_that( challenger, validly_provides(IChallenger) )

	# Challenging produces as 401, but without a WWW-Authenticate header
	unauth = challenger.challenge( {}, '401', {}, [] )
	assert_that( unauth.headers, does_not( has_key( 'WWW-Authenticate' ) ) )
	assert_that( unauth.headers, has_key( 'Content-Type' ) )

	# forgetting adds no headers
	assert_that( challenger.forget( {}, {} ), is_( () ) )

def test_request_classifier():

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

def test_decode_bad_auth():
	req = Request.blank('/')

	# blank password
	req.authorization = ('Basic', 'username:'.encode('base64') )

	username, password = _decode_username_request( req )

	assert_that( username, is_( 'username' ) )
	assert_that( password, is_( '' ) )

	# malformed header
	req.authorization = ('Basic', 'username'.encode('base64') )

	username, password = _decode_username_request( req )

	assert_that( username, is_( none() ) )
	assert_that( password, is_( none() ) )

	# blank username
	req.authorization = ('Basic', ':foo'.encode('base64') )
	username, password = _decode_username_request( req )

	assert_that( username, is_( '' ) )
	assert_that( password, is_( 'foo' ) )
