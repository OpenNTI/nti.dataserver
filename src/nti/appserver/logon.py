#!/usr/bin/env python
"""
Views and data models relating to the login process.
"""

from __future__ import print_function, unicode_literals


from zope import interface
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.links import Link
from nti.dataserver import mimetype

from pyramid.view import view_config, render_view_to_response
from pyramid import security as sec
import pyramid.request
import pyramid.httpexceptions as hexc

REL_HANDSHAKE = 'logon.handshake'
REL_CONTINUE  = 'logon.continue'

REL_LOGIN_NTI_PASSWORD = 'logon.nti.password'
REL_LOGIN_GOOGLE = 'logon.google'

def _links_for_authenticated_users( request ):
	"""
	If a request is authenticated, returns links that should
	go to the user. Shared between ping and handshake.
	"""
	links = ()
	remote_user_name = sec.authenticated_userid( request )
	if remote_user_name:
		# They are already logged in, provide a continue link
		continue_href = request.route_path( 'user.root.service', _='' )
		links = ( Link( continue_href, rel=REL_CONTINUE ), )
	return links

@view_config(route_name='logon.ping', request_method='GET', renderer='rest')
def ping( request ):
	"""
	The first step in authentication.

	:return: An externalizable object containing a link to the handshake URL, and potentially
	to the continue URL if authentication was valid.
	"""
	links = []
	handshake_href = request.route_path( 'logon.handshake' )
	links.append( Link( handshake_href, rel=REL_HANDSHAKE ) )
	links.extend( _links_for_authenticated_users( request ) )

	return _Pong( links )

class _Pong(dict):
	interface.implements( nti_interfaces.IExternalObject )

	__external_class_name__ = 'Pong'
	mime_type = mimetype.nti_mimetype_with_class( 'pong' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks


@view_config(route_name=REL_HANDSHAKE, request_method='POST', renderer='rest')
def handshake(request):
	"""
	The second step in authentication. Inspects provided credentials
	to decide what sort of logins are possible.
	"""

	desired_username = request.params.get( 'username' )
	if not desired_username:
		return hexc.HTTPBadRequest(detail="Must provide username")

	links = []

	# TODO: Check for existence in the database before generating these.
	# We also need to be validating whether we can do a openid login, etc.
	links.append( Link( request.route_path( REL_LOGIN_NTI_PASSWORD ), rel=REL_LOGIN_NTI_PASSWORD ) )


	links.append( Link( request.route_path( REL_LOGIN_GOOGLE ),
						rel=REL_LOGIN_GOOGLE ) )


	links.extend( _links_for_authenticated_users( request ) )

	return _Handshake( links )

class _Handshake(dict):
	interface.implements( nti_interfaces.IExternalObject )

	__external_class_name__ = 'Handshake'
	mime_type = mimetype.nti_mimetype_with_class( 'handshake' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks

def _create_failure_response( request ):
	response = None
	if request.params.get( 'failure' ):
		response = hexc.HTTPSeeOther( location=request.params.get( 'failure' ) )
	else:
		response = hexc.HTTPUnauthorized()
	# Clear any cookies they sent that failed.
	response.headers.extend( sec.forget(request) )

	return response

def _create_success_response( request, userid=None ):
	# Incoming authentication worked. Remember the user, and
	# either redirect or no-content
	if request.params.get( 'success' ):
		response = hexc.HTTPSeeOther( location=request.params.get( 'success' ) )
	else:
		response = hexc.HTTPNoContent()
	if userid is None:
		userid = sec.authenticated_userid( request )

	response.headers.extend( sec.remember( request, userid ) )
	return response


@view_config(route_name=REL_LOGIN_NTI_PASSWORD, request_method='GET', renderer='rest')
def password_logon(request):
	response = None

	if not sec.authenticated_userid(request):
		response = _create_failure_response( request )
	else:
		response = _create_success_response( request )
	return response

import pyramid_openid.view

@view_config(route_name=REL_LOGIN_GOOGLE, request_method="GET")
def google_login(context, request):
	nrequest = pyramid.request.Request.blank( request.route_url( 'logon.google.result', _query=request.params ),
											  POST={'openid2': 'https://www.google.com/accounts/o8/id'} )
	nrequest.registry = request.registry
	# TODO: Why can't I use this API?
#	return render_view_to_response(context, nrequest, name='verify_openid')
	return pyramid_openid.view.verify_openid( context, nrequest )

@view_config(route_name="logon.google.result", request_method='GET')
def google_response(context, request):
	"""
	Process an OpenID response from google. This exists as a wrapper around
	:func:`pyramid_openid.view.verify_openid` because that function
	does nothing in failure, but we need to know about failure. (This is as-of
	0.3.4; it is fixed in trunk.)
	"""
	response = None
	openid_mode = request.params.get( 'openid.mode', None )
	if openid_mode != 'id_res':
		# Failure.
		response = _create_failure_response( request )
	else:
		response = pyramid_openid.view.verify_openid( context, request )
	return response

def _openidcallback( context, request, success_dict ):
	# Google only supports AX, sreg is ignored.
	# Each of these comes back as a list, for some reason
	fname = success_dict.get( 'ax', {} ).get('firstname', [''])[0]
	lname = success_dict.get( 'ax', {} ).get('lastname', [''])[0]
	email = success_dict.get( 'ax', {} ).get('email', [''])[0]
	langu = success_dict.get( 'ax', {} ).get('language', [''])[0]
	idurl = success_dict.get( 'identity_url' )
	# TODO: Creating user object, etc
	# The webapp actually needs its own cookie that we are not currently providing, so a simple
	# redirect won't cut it. It's going to take some deeper cooperation.
	return _create_success_response( request, userid=email )
