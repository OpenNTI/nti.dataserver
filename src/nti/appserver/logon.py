#!/usr/bin/env python
"""
Views and data models relating to the login process.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from zope import interface, component, lifecycleevent
from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces

from nti.dataserver.links import Link
from nti.dataserver import mimetype
from nti.dataserver import users

from pyramid.view import view_config
from pyramid import security as sec
import pyramid.interfaces
import pyramid.request
import pyramid.httpexceptions as hexc

import requests
import urllib
import anyjson as json

REL_HANDSHAKE = 'logon.handshake'
REL_CONTINUE  = 'logon.continue'

REL_LOGIN_NTI_PASSWORD = 'logon.nti.password'
REL_LOGIN_GOOGLE = 'logon.google'
REL_LOGIN_OPENID = 'logon.openid'
REL_LOGIN_FACEBOOK = 'logon.facebook'
REL_LOGIN_LOGOUT = 'logon.logout'

def _links_for_authenticated_users( request ):
	"""
	If a request is authenticated, returns links that should
	go to the user. Shared between ping and handshake.
	"""
	links = ()
	remote_user_name = sec.authenticated_userid( request )
	if remote_user_name:
		logger.debug( "Found authenticated user %s", dict(request.environ.get( 'repoze.who.identity', {} )) )
		# They are already logged in, provide a continue link
		continue_href = request.route_path( 'user.root.service', _='' )
		links = [ Link( continue_href, rel=REL_CONTINUE ) ]
		logout_href = request.route_path( REL_LOGIN_LOGOUT )
		links.append( Link( logout_href, rel=REL_LOGIN_LOGOUT ) )

	return links

def _forgetting( request, redirect_param_name, no_param_class, redirect_value=None, error=None ):
	response = None
	if redirect_value is None:
		redirect_value = request.params.get( redirect_param_name )
	if redirect_value:
		response = hexc.HTTPSeeOther( location=redirect_value )
	else:
		response = no_param_class()
	# Clear any cookies they sent that failed.
	response.headers.extend( sec.forget(request) )
	if error:
		response.headers['Warning'] = [error]

	return response

@view_config(route_name=REL_LOGIN_LOGOUT, request_method='GET')
def logout(request):
	return _forgetting( request, 'success', hexc.HTTPNoContent )

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

class NoSuchUser(object):
	interface.implements( app_interfaces.IMissingUser )

	def __init__( self, username ):
		self.username = username

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
	user = users.User.get_user( username=desired_username,
								dataserver=request.registry.getUtility(nti_interfaces.IDataserver) )

	if user is None:
		user = NoSuchUser(desired_username)

	links = {}
	for provider in request.registry.subscribers( (user,request), app_interfaces.ILogonLinkProvider ):
		if provider.rel in links:
			continue
		link = provider()
		if link is not None:
			links[link.rel] = link


	links = list( links.values() )

	links.extend( _links_for_authenticated_users( request ) )

	return _Handshake( links )

class _SimpleExistingUserLinkProvider(object):
	interface.implements( app_interfaces.ILogonLinkProvider )
	component.adapts( nti_interfaces.IUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_NTI_PASSWORD

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__(self):
		if self.user.has_password():
			return Link( self.request.route_path( REL_LOGIN_NTI_PASSWORD ), rel=REL_LOGIN_NTI_PASSWORD )

class _SimpleMissingUserFacebookLinkProvider(object):
	interface.implements( app_interfaces.ILogonLinkProvider )
	component.adapts( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_FACEBOOK

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__(self):
		return Link( self.request.route_path( 'logon.facebook.oauth1' ), rel=self.rel )

class _SimpleExistingUserFacebookLinkProvider(_SimpleMissingUserFacebookLinkProvider):
	component.adapts( nti_interfaces.IFacebookUser, pyramid.interfaces.IRequest )


class _WhitelistedDomainGoogleLoginLinkProvider(object):
	interface.implements( app_interfaces.ILogonLinkProvider )
	component.adapts( nti_interfaces.IUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_GOOGLE

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	# TODO: We are never checking that the user we get actually comes
	# from one of these domains.
	domains = ['nextthought.com', 'gmail.com']
	def __call__( self ):
		if getattr( self.user, 'identity_url', None ) is not None:
			# They have a specific ID already, they don't need this
			return None

		domain = self.user.username.split( '@' )[-1]
		if domain in self.domains:
			oidcsum = str(hash(self.user.username))
			return Link( self.request.route_path( REL_LOGIN_GOOGLE, _query={'oidcsum': oidcsum} ),
						  rel=REL_LOGIN_GOOGLE )

class _MissingUserWhitelistedDomainGoogleLoginLinkProvider(_WhitelistedDomainGoogleLoginLinkProvider):
	component.adapts( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )


class _ExistingOpenIdUserLoginLinkProvider(object):
	component.adapts( nti_interfaces.IOpenIdUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_OPENID

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__( self ):
		oidcsum = str(hash(self.user.username))
		return Link( self.request.route_path( REL_LOGIN_OPENID, _query={'openid': self.user.identity_url,
																		'oidcsum': oidcsum} ),
					 rel=REL_LOGIN_OPENID )


class _Handshake(dict):
	interface.implements( nti_interfaces.IExternalObject )

	__external_class_name__ = 'Handshake'
	mime_type = mimetype.nti_mimetype_with_class( 'handshake' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks

def _create_failure_response( request, failure=None, error=None ):
	return _forgetting( request, 'failure', hexc.HTTPUnauthorized, redirect_value=failure )

def _create_success_response( request, userid=None, success=None ):
	# Incoming authentication worked. Remember the user, and
	# either redirect or no-content
	if success is None:
		success = request.params.get( 'success' )
	if success:
		response = hexc.HTTPSeeOther( location=success )
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

def _openid_login(context, request, openid='https://www.google.com/accounts/o8/id', params=None):
	if params is None:
		params = request.params
	if 'oidcsum' not in params:
		logger.warn( "oidcsum not present" )
		return _create_failure_response( request )

	nrequest = pyramid.request.Request.blank( request.route_url( 'logon.google.result', _query=params ),
											  # In theory, if we're constructing the URL correctly, this is enough
											  # to carry through HTTPS info
											  base_url=request.host_url,
											  POST={'openid2': 'https://www.google.com/accounts/o8/id'} )
	logger.debug( "Directing pyramid request to %s", nrequest )
	nrequest.registry = request.registry
	return pyramid_openid.view.verify_openid( context, nrequest )

@view_config(route_name=REL_LOGIN_GOOGLE, request_method="GET")
def google_login(context, request):
	return _openid_login( context, request )

@view_config(route_name=REL_LOGIN_OPENID, request_method="GET")
def openid_login(context, request):
	params = dict(request.params)
	if 'oidcsum' not in params:
		params['oidcsum'] = str(hash(request.params.get('openid')))
	return _openid_login( context, request, request.params.get( 'openid' ), params )

@view_config(route_name="logon.google.result")#, request_method='GET')
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

def _deal_with_external_account( request, fname, lname, email, idurl, iface, creator ):
	#print( "User ", email, " belongs to ", idurl )
	dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
	user = users.User.get_user( username=email, dataserver=dataserver )
	url_attr = iface.names()[0]
	if user:
		if not iface.providedBy( user ):
			interface.alsoProvides( user, iface )
			setattr( user, url_attr, idurl )
			lifecycleevent.modified( user, lifecycleevent.Attributes( iface, url_attr ) )
			# TODO: Can I assign to persistent object's __class__? Should I?
		assert getattr( user, url_attr ) == idurl
	else:
		# This fires lifecycleevent.IObjectAddedEvent. The oldParent attribute
		# will be None
		kwargs = {'dataserver': dataserver,
				  'username': email,
				  'password': '',
				  'realname': fname + ' ' + lname }
		kwargs[url_attr] = idurl
		user = creator.create_user( **kwargs )
		assert getattr( user, url_attr ) == idurl
	return user


def _openidcallback( context, request, success_dict ):
	# It seems that the identity_url is actually
	# ignored by google and we get back identifying information for
	# whatever user is currently signed in. This can have strange consequences
	# with mismatched URLs and emails (you are signed in, but not as who you
	# indicated you wanted to be signed in as): It's not a security problems because
	# we use the credentials you actually authenticated with, its just confusing.
	# To try to prevent this, we are using a basic checksum approach to see if things
	# match: oidcsum.

	# Google only supports AX, sreg is ignored.
	# Each of these comes back as a list, for some reason
	fname = success_dict.get( 'ax', {} ).get('firstname', [''])[0]
	lname = success_dict.get( 'ax', {} ).get('lastname', [''])[0]
	email = success_dict.get( 'ax', {} ).get('email', [''])[0]
	idurl = success_dict.get( 'identity_url' )
	oidcsum = request.params.get( 'oidcsum' )
	if str(hash(email)) != oidcsum:
		   logger.warn( "Checksum mismatch. Logged in multiple times?")
		   return _create_failure_response(request, error='Email checksum mismatch')

	try:
		_deal_with_external_account( request, fname, lname, email, idurl, nti_interfaces.IOpenIdUser, users.OpenIdUser )
	except Exception as e:
		return _create_failure_response( request, error=str(e) )


	return _create_success_response( request, userid=email )



@view_config( route_name='logon.facebook.oauth1', request_method='GET' )
def facebook_oauth1( request ):
	app_id = request.registry.settings.get( 'facebook.app.id' )
	our_uri = urllib.quote( request.route_url( 'logon.facebook.oauth2' ) )
	# We seem incapable of sending any parameters with the redirect_uri. If we do,
	# then the validation step 400's.
	for k in ('success','failure'):
		if request.params.get( k ):
			request.session['facebook.' + k] = request.params.get( k )

	redir_to = 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=email' % (app_id, our_uri)

	return hexc.HTTPSeeOther( location=redir_to )

@view_config( route_name='logon.facebook.oauth2', request_method='GET' )
def facebook_oauth2(request):
	if 'error' in request.params:
		return _create_failure_response( request )

	code = request.params['code']
	app_id = request.registry.settings.get( 'facebook.app.id' )
	our_uri = urllib.quote( request.route_url( 'logon.facebook.oauth2' ))#, _query={'success': request.params.get('success', ''),
																		#		'failure': request.params.get('failure', '') } ) )
	app_secret = request.registry.settings.get( 'facebook.app.secret' )

	auth = requests.get( 'https://graph.facebook.com/oauth/access_token?client_id=%s&redirect_uri=%s&client_secret=%s&code=%s' % (app_id, our_uri,app_secret, code) )
	try:
		auth.raise_for_status()
	except:
		return _create_failure_response(request, request.session.get('facebook.failure'))

	text = auth.text
	token = None
	for x in text.split( '&'):
		if x.startswith('access_token='):
			token = x[len('access_token='):]
			break

	data = requests.get( 'https://graph.facebook.com/me?access_token=' + token )
	data = json.loads( data.text )
	_deal_with_external_account( request,
								 data['first_name'], data['last_name'],
								 data['email'], data['link'],
								 nti_interfaces.IFacebookUser,
								 users.FacebookUser )

	return _create_success_response( request, userid=data['email'], success=request.session.get('facebook.success') )
