#!/usr/bin/env python
"""
Views and data models relating to the login process.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from zope import interface, component, lifecycleevent
from zope.event import notify
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.appserver import interfaces as app_interfaces

from nti.dataserver.links import Link
from nti.dataserver import mimetype
from nti.dataserver import users

from pyramid.view import view_config
from pyramid import security as sec
import pyramid.interfaces
import pyramid.request
import pyramid.httpexceptions as hexc

import logilab.common.cache
import requests
import gevent
from requests.exceptions import RequestException
# Note that we do not use requests.async/grequests.
# It wants to monkey patch far too much of the system (on import!)
# and is not compatible with ZODB (patch to time). We think
# our patching of socket and ssl in application.py is sufficient (?)
# TODO: It looks like the incompatibilities are fixed with 1.0. application.py
# will be doing some work with this. Once confirmed, decide what to do here
# (the non-async api is prettier, but 'prefetch' might be helpful?)
#import grequests # >= 0.13.0
#import requests.async # <= 0.12.1

import urllib
import urlparse
import anyjson as json

REL_HANDSHAKE = 'logon.handshake'
REL_CONTINUE  = 'logon.continue'

REL_LOGIN_NTI_PASSWORD = 'logon.nti.password'
REL_LOGIN_GOOGLE = 'logon.google'
REL_LOGIN_OPENID = 'logon.openid'
REL_LOGIN_FACEBOOK = 'logon.facebook'
REL_LOGIN_LOGOUT = 'logon.logout'

# The time limit for a GET request during
# the authentication process
_REQUEST_TIMEOUT = 0.5

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
	if not redirect_value:
		redirect_value = request.params.get( redirect_param_name )

	if redirect_value:
		if error:
			parsed = urlparse.urlparse( redirect_value )
			parsed = list(parsed)
			query = parsed[4]
			if query:
				query = query + '&error=' + urllib.quote( error )
			else:
				query = 'error=' + urllib.quote( error )
			parsed[4] = query
			redirect_value = urlparse.urlunparse( parsed )

		response = hexc.HTTPSeeOther( location=redirect_value )
	else:
		response = no_param_class()
	# Clear any cookies they sent that failed.
	response.headers.extend( sec.forget(request) )
	if error:
		# TODO: Sending multiple warnings
		response.headers['Warning'] = error

	logger.debug( "Forgetting user %s with %s (%s)", sec.authenticated_userid(request), response, response.headers )
	return response

@view_config(route_name=REL_LOGIN_LOGOUT, request_method='GET')
def logout(request):
	# Terminate any sessions they have open
	# TODO: We need to associate the socket.io session somehow
	# so we can terminate just that one session (we cannot terminate all,
	# multiple logins are allowed )
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
	interface.implements( ext_interfaces.IExternalObject )

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
			return Link( self.request.route_path( REL_LOGIN_NTI_PASSWORD, _query={'username': self.user.username}),
						 rel=REL_LOGIN_NTI_PASSWORD )

class _SimpleMissingUserFacebookLinkProvider(object):
	interface.implements( app_interfaces.ILogonLinkProvider )
	component.adapts( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_FACEBOOK

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__(self):
		return Link( self.request.route_path( 'logon.facebook.oauth1', _query={'username': self.user.username} ),
					 rel=self.rel )

class _SimpleExistingUserFacebookLinkProvider(_SimpleMissingUserFacebookLinkProvider):
	component.adapts( nti_interfaces.IFacebookUser, pyramid.interfaces.IRequest )


def _prepare_oid_link( request, username, rel, params=None ):
	query = {} if params is None else dict(params)
	oidcsum = str(hash(username))
	query['oidcsum'] = oidcsum
	query['username'] = username
	try:
		return Link( request.route_path( rel, _query=query ),
					 rel=rel )
	except KeyError:
		# This is really a programmer/configuration error,
		# but we let it pass for tests
		logger.exception( "Unable to direct to route %s", rel )
		return

class _WhitelistedDomainGoogleLoginLinkProvider(object):
	interface.implements( app_interfaces.ILogonLinkProvider )
	component.adapts( nti_interfaces.IUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_GOOGLE

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	# TODO: We are never checking that the user we get actually comes
	# from one of these domains. Should we? Does it matter?
	domains = ['nextthought.com', 'gmail.com']
	def __call__( self ):
		if getattr( self.user, 'identity_url', None ) is not None:
			# They have a specific ID already, they don't need this
			return None

		domain = self.user.username.split( '@' )[-1]
		if domain in self.domains:
			return _prepare_oid_link( self.request, self.user.username, self.rel )

class _MissingUserWhitelistedDomainGoogleLoginLinkProvider(_WhitelistedDomainGoogleLoginLinkProvider):
	component.adapts( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )

class _OnlineQueryGoogleLoginLinkProvider(object):
	"""
	Queries google to see if the domain is an Apps domain that
	we can expect to use google auth on.
	"""

	interface.implements( app_interfaces.ILogonLinkProvider )
	component.adapts( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )

	KNOWN_DOMAIN_CACHE = logilab.common.cache.Cache()

	rel = REL_LOGIN_GOOGLE

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__( self ):
		domain = self.user.username.split( '@' )[-1]
		allow = False
		cached = self.KNOWN_DOMAIN_CACHE.get( domain )
		if cached is not None:
			allow = cached
		else:
			try:
				google_rsp = requests.get( 'https://www.google.com/accounts/o8/.well-known/host-meta',
										   params={'hd': domain},
										   timeout=_REQUEST_TIMEOUT )
			except RequestException:
				# Timeout, no resolution, nothing to cache
				logger.info( "Timeout checking Google apps account for %s", domain )
				return None
			else:
				allow = google_rsp.status_code == 200
				self.KNOWN_DOMAIN_CACHE[domain] = allow

		if allow:
			return _prepare_oid_link( self.request, self.user.username, self.rel )

class _ExistingOpenIdUserLoginLinkProvider(object):
	component.adapts( nti_interfaces.IOpenIdUser, pyramid.interfaces.IRequest )

	rel = REL_LOGIN_OPENID

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__( self ):
		return _prepare_oid_link( self.request, self.user.username, self.rel, params={'openid': self.user.identity_url} )


class _Handshake(dict):
	interface.implements( ext_interfaces.IExternalObject )

	__external_class_name__ = 'Handshake'
	mime_type = mimetype.nti_mimetype_with_class( 'handshake' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks

def _create_failure_response( request, failure=None, error=None ):
	return _forgetting( request, 'failure', hexc.HTTPUnauthorized, redirect_value=failure, error=error )

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

	# Send the logon event
	dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
	user = users.User.get_user( username=userid, dataserver=dataserver )
	notify( app_interfaces.UserLogonEvent( user, request ) )

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
		logger.warn( "oidcsum not present in %s at %s", params, request )
		return _create_failure_response( request, error="Invalid params; missing oidcsum" )


	openid_field = request.registry.settings.get('openid.param_field_name', 'openid')
	nrequest = pyramid.request.Request.blank( request.route_url( 'logon.google.result', _query=params ),
											  # In theory, if we're constructing the URL correctly, this is enough
											  # to carry through HTTPS info
											  base_url=request.host_url,
											  POST={openid_field: openid } )
	logger.debug( "Directing pyramid request to %s", nrequest )
	nrequest.registry = request.registry
	# If the discover process fails, the view will do two things:
	# (1) Flash a message in the session queue request.settings.get('openid.error_flash_queue', '')
	# (2) redirect to request.settings.get( 'openid.errordestination', '/' )
	# We have a better way to return errors, and we want to use it,
	# so we scan for the error_flash.
	# NOTE: We are assuming that neither of these is configured, and that
	# nothing else uses the flash queue
	q_name = request.registry.settings.get( 'openid.error_flash_queue', '' )
	q_b4 = nrequest.session.pop_flash( q_name )
	assert len(q_b4) == 0

	result = pyramid_openid.view.verify_openid( context, nrequest )

	q_after = nrequest.session.pop_flash(q_name)
	if result is None:
		# This is a programming/configuration error in 0.3.4, meaning we have
		# failed to pass required params. For example, the openid_param_name might not match
		raise AssertionError( "Failure to get response object; check configs" )
	elif q_after != q_b4:
		# Error
		result = _create_failure_response( request, error=q_after[0] )
	return result

@view_config(route_name=REL_LOGIN_GOOGLE, request_method="GET")
def google_login(context, request):
	return _openid_login( context, request )

@view_config(route_name=REL_LOGIN_OPENID, request_method="GET")
def openid_login(context, request):
	if 'openid' not in request.params:
		return _create_failure_response( request, error='Missing openid' )
	return _openid_login( context, request, request.params['openid'] )

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

STATIC_COMMUNITIES = ('MathCounts',)
from zope.lifecycleevent.interfaces import IObjectAddedEvent, IObjectModifiedEvent
@component.adapter(nti_interfaces.IUser,IObjectAddedEvent)
def add_new_user_to_static_communities( user, object_added_event ):
	# Ultimately there should be a bunch of stuff that gets done
	# when users are added, based on...some heuristics...
	# in the immediate term, we will add new users to some pre-defined
	# communities, if they exist
	if object_added_event.oldParent:
		# Only for new users
		return
	for com_name in STATIC_COMMUNITIES:
		# If we're fired during migration, we may not be
		# able to resolve entities (no IDataserver) so we need to
		# provide a non-None default
		community = users.Entity.get_entity( com_name, default='' )
		if community:
			user.join_community( community )
			user.follow( community )

@component.adapter(nti_interfaces.IUser,app_interfaces.IUserLogonEvent)
def _user_did_logon( user, event ):
	user.update_last_login_time()



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

###
# TODO: The two facebook methods below could be radically simplified using
# requests-facebook. As of 0.1.1, it adds no dependencies. (However, it also has no tests in its repo)
# http://pypi.python.org/pypi/requests-facebook/0.1.1
###

@view_config( route_name='logon.facebook.oauth1', request_method='GET' )
def facebook_oauth1( request ):
	app_id = request.registry.settings.get( 'facebook.app.id' )
	our_uri = urllib.quote( request.route_url( 'logon.facebook.oauth2' ) )
	# We seem incapable of sending any parameters with the redirect_uri. If we do,
	# then the validation step 400's. Thus we resort to the session
	for k in ('success','failure'):
		if request.params.get( k ):
			request.session['facebook.' + k] = request.params.get( k )

	request.session['facebook.username'] = request.params.get('username')
	redir_to = 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=email' % (app_id, our_uri)

	return hexc.HTTPSeeOther( location=redir_to )

@view_config( route_name='logon.facebook.oauth2', request_method='GET' )
def facebook_oauth2(request):

	if 'error' in request.params:
		return _create_failure_response( request, request.session.get('facebook.failure'), error=request.params.get('error') )

	code = request.params['code']
	app_id = request.registry.settings.get( 'facebook.app.id' )
	our_uri = request.route_url( 'logon.facebook.oauth2' )
	app_secret = request.registry.settings.get( 'facebook.app.secret' )

	auth = requests.get( 'https://graph.facebook.com/oauth/access_token',
						 params={'client_id': app_id, 'redirect_uri': our_uri, 'client_secret': app_secret, 'code': code},
						 timeout=_REQUEST_TIMEOUT )

	try:
		auth.raise_for_status()
	except RequestException as req_ex:
		logger.exception( "Failed facebook login %s", auth.text )
		return _create_failure_response(request, request.session.get('facebook.failure'), error=str(req_ex))


	# The facebook return value is in ridiculous format.
	# Are we supposed to try to treat this like a url query value or
	# something? Yick.
	# TODO: try urlparse.parse_qsl. We need test cases!
	text = auth.text
	token = None
	for x in text.split( '&'):
		if x.startswith('access_token='):
			token = x[len('access_token='):]
			break

	# For the data formats, see here:
	# https://developers.facebook.com/docs/reference/api/user/
	# Fire off requests for the user's data that we want, plus
	# the address of his picture. The picture we can use later,
	# so let it prefetch
	pic_rsp = requests.get( 'https://graph.facebook.com/me/picture',
							params={'access_token': token},
							allow_redirects=False, # This should return a 302, we want the location, not the data
							timeout=_REQUEST_TIMEOUT,
							return_response=False,
							prefetch=True,
							config={'safe_mode': True} )
	pic_glet = gevent.spawn(pic_rsp.send)

	data = requests.get( 'https://graph.facebook.com/me',
						 params={'access_token': token},
						 timeout=_REQUEST_TIMEOUT )
	data = json.loads( data.text )
	if data['email'] != request.session.get('facebook.username'):
		logger.warn( "Facebook username returned different emails %s != %s", data['email'], request.session.get('facebook.username') )
		return _create_failure_response( request, request.session.get('facebook.failure'), error='Facebook resolved to different username' )

	user = _deal_with_external_account( request,
										data['first_name'], data['last_name'],
										data['email'], data['link'],
										nti_interfaces.IFacebookUser,
										users.FacebookUser )
	# Do we have a facebook picture to use? If so, snag it and use it.
	pic_glet.join()
	pic_rsp = pic_rsp.response
	if pic_rsp.status_code == 302:
		pic_location = pic_rsp.headers['Location']
		if pic_location and pic_location != user.avatarURL:
			user.avatarURL = pic_location

	return _create_success_response( request, userid=data['email'], success=request.session.get('facebook.success') )
