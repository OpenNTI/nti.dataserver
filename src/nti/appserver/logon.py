#!/usr/bin/env python
"""
Views and data models relating to the login process.
"""

from __future__ import print_function, unicode_literals


from zope import interface
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.links import Link
from nti.dataserver import mimetype

from pyramid.view import view_config
from pyramid import security as sec
import pyramid.httpexceptions as hexc

REL_HANDSHAKE = 'logon.handshake'
REL_CONTINUE  = 'logon.continue'

REL_LOGIN_NTI_PASSWORD = 'logon.nti.password'

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


	links.extend( _links_for_authenticated_users( request ) )

	return _Handshake( links )

class _Handshake(dict):
	interface.implements( nti_interfaces.IExternalObject )

	__external_class_name__ = 'Handshake'
	mime_type = mimetype.nti_mimetype_with_class( 'handshake' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks



@view_config(route_name=REL_LOGIN_NTI_PASSWORD, request_method='GET', renderer='rest')
def password_logon(request):
	response = None

	if not sec.authenticated_userid(request):
		# Incoming authentication failed. Redirect or error
		if request.params.get( 'failure' ):
			response = hexc.HTTPSeeOther( location=request.params.get( 'failure' ) )
		else:
			response = hexc.HTTPUnauthorized()
		# Clear any cookies they sent that failed.
		response.headers.extend( sec.forget(request) )
	else:
		# Incoming authentication worked. Remember the user, and
		# either redirect or no-content
		if request.params.get( 'success' ):
			response = hexc.HTTPSeeOther( location=request.params.get( 'success' ) )
		else:
			response = hexc.HTTPNoContent()

		response.headers.extend( sec.remember( request, sec.authenticated_userid( request ) ) )
	return response
