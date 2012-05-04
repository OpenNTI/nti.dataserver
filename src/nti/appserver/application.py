#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

# Import this first to ensure gevent is monkey patched
import nti.dataserver as dataserver

import gevent.local

import sys
import os
import traceback

import UserDict

import nti.dictserver as dictserver
import nti.dictserver.dictionary


#Hmm, these next three MUST be imported. We seem to have a path-dependent import req.
import nti.dataserver._Dataserver

#from nti.dataserver.library import Library
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
contentsearch = nti.contentsearch
import nti.contentsearch.indexmanager

import nti.dataserver.users
from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserver


from zope import interface
from zope import component
from zope.configuration import xmlconfig
from zope.event import notify
from zope.processlifetime import ProcessStarting
from zope.component.hooks import setSite, getSite, setHooks, siteinfo
assert gevent.local.local in type(siteinfo).__bases__
import transaction

import nti.appserver.workspaces

import pyramid.config
import pyramid.authorization
import pyramid.security
import pyramid.httpexceptions as hexc

import datetime
import pyramid_zodbconn

from . import pyramid_auth


# Make the zope interface extend the pyramid interface
# Although this seems backward, it isn't. The zope location
# proxy implements the zope interface, and we want
# that to match with pyramid
from pyramid.interfaces import ILocation
from zope.location.interfaces import ILocation as IZLocation
IZLocation.__bases__ = (ILocation,)

#from zope import container as zcontainer
#from zope import location as zlocation

SOCKET_IO_PATH = 'socket.io'

#TODO: we should do this as configuration
DATASERVER_WHOOSH_INDEXES = 'DATASERVER_WHOOSH_INDEXES' in os.environ

class _Main(object):

	def __init__(self, pyramid_config, serveFiles=(), http_port=8080):
		self.serveFiles = [ ('/dictionary', None) ]
		self.http_port = http_port
		self.pyramid_config = pyramid_config
		self.pyramid_app = None

	def addServeFiles( self, serveFile ):
		self.serveFiles.append( serveFile )

	def setServeFiles( self, serveFiles=() ):
		self.serveFiles.extend( list(serveFiles) )

		for prefix, path  in serveFiles:
			# Note: We are not configuring caching for these files, nor gzip. In production
			# usage, we MUST be behind a webserver that will deal with static
			# files correctly (nginx, apache) by applying ETags to allow caching and Content-Encoding
			# for speed.
			self.pyramid_config.add_static_view( prefix, path )
		self.pyramid_config.add_static_view( SOCKET_IO_PATH + '/static/', 'nti.socketio:static/' )
		self.serveFiles.append( ( '/' + SOCKET_IO_PATH + '/static/', None ) )
		self.pyramid_app = self.pyramid_config.make_wsgi_app()

	def __call__(self, environ, start_request):

		# For CORS preflight requests, we must support the OPTIONS
		# method.
		# TODO: The OPTIONS method should be better implemented.
		if environ['REQUEST_METHOD'] == 'OPTIONS':
			start_request( '200 OK', [('Content-Type', 'text/plain')] )
			return [""]


		# Nothing seems to actually be supporting the same
		# WebSocket protocol versions.

		# Firefox 5 and 6 have nothing. Socket.io uses
		# long-connections with xhr-multipart for it.

		# All tested versions of Safari (5.1 lion, 5.0 on lion,
		# nightly) seems to run version 76 of the protocol (KEY1
		# and KEY2), and so it connects just fine over websockets.
		# NOTE: the source document must be served over HTTP.
		# Local files don't work without a hack to avoid checking HTTP_ORIGIN

		# Safari on iOS 5 is the same as desktop.

		# Chrome 14.0.835.122 beta is the new version 7 or 8.
		# Chrome 15.0.865.0 dev is the same as Chrome 14.
		# Chrome 16 is version 13 (which seems to be compatible with 7/8)

		if environ['PATH_INFO'].startswith( '/stacktraces' ):
			# TODO: Extend to greenlets
			code = []
			for threadId, stack in sys._current_frames().items():
				code.append("\n# ThreadID: %s" % threadId)
				for filename, lineno, name, line in traceback.extract_stack(stack):
					code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
					if line:
						code.append("  %s" % (line.strip()))
			body = '\n'.join(code)
			print body
			start_request( '200 OK', [('Content-Type', 'text/plain'),] )
			return body + '\n'

		return self.pyramid_app( environ, start_request )
import pyramid_tm
def site_tween_factory(handler, registry):
	# Our site setup
	# If we wanted to, we could be setting sites up as we traverse as well
	setHooks()
	def early_request_teardown(request):
		"""
		Clean up all the things set up by our new request handler and the
		tweens. Call this function if the request thread will not be returning,
		but these resources should be cleaned up.
		"""
		transaction.commit()
		pyramid_zodbconn.get_connection(request).close()
		setSite( None )
		# Remove the close action that pyramid_zodbconn wants to do.
		# The connection might have been reused by then.
		for callback in request.finished_callbacks:
			if getattr( callback, '__module__', None ) == pyramid_zodbconn.__name__:
				request.finished_callbacks.remove( callback )
				break

	def site_tween( request ):
		"""
		Within the scope of a transaction, gets a connection and installs our
		site manager. Records the active user and URL in the transaction.
		"""
		conn = pyramid_zodbconn.get_connection( request )
		conn.sync()
		site = conn.root()['nti.dataserver']
		old_site = getSite()
		# Not sure what circumstances lead to already having a site
		# here. Have seen it at startup. Force it back to none (?)
		# It is very bad to raise an exception here, it interacts
		# badly with logging
		try:
			assert old_site is None, "Should not have a site already in place"
		except AssertionError:
			logger.exception( "Should not have a site already in place: %s", old_site )
			old_site = None

		setSite( site )
		try:
			# Now (and only now, that the site is setup) record info in the transaction
			uid = pyramid.security.authenticated_userid( request )
			if uid:
				transaction.get().setUser( uid )
			transaction.get().note( request.url )
			request.environ['nti.early_request_teardown'] = early_request_teardown
			response = handler(request)
			### FIXME:
			# pyramid_tm <= 0.4 has a bug in that if committing raises a retryable exception,
			# it doesn't actually retry (because commit is inside the __exit__ of a context
			# manager, and a normal exit ignores the return value of __exit__, so the loop
			# doesn't actually loop: the return statement trumps).
			# Thus, we commit here so that an exception is raised and caught.
			# See https://github.com/Pylons/pyramid_tm/issues/4
			if not transaction.isDoomed() and not pyramid_tm.default_commit_veto( request, response ):
				transaction.commit()
			return response
		finally:
			setSite()

	return site_tween

def createApplication( http_port,
					   library,
					   process_args=False,
					   create_ds=True,
					   pyramid_config=None,
					   **settings ):
	"""
	:return: A tuple (wsgi app, _Main)
	"""
	server = None
	# Configure subscribers, etc.
	xmlconfig.file( 'configure.zcml', package=nti.appserver )

	# Notify of startup. (Note that configuring the packages loads zope.component:configure.zcml
	# which in turn hooks up zope.component.event to zope.event for event dispatching)
	notify( ProcessStarting() )

	logger.debug( 'Began starting dataserver' )
	server = None

	if IDataserver.providedBy( create_ds ): #not isinstance( create_ds, bool ):
		server = create_ds
	elif not create_ds:
		class MockServer(object):
			_parentDir = '.'
			_dataFileName = 'data.fs'
		server = MockServer()
	else:
		ds_class = dataserver._Dataserver.Dataserver
		if process_args:
			dataDir = "~/tmp"
			dataFile = "test.fs"
			if '--dataDir' in sys.argv: dataDir = sys.argv[sys.argv.index('--dataDir') + 1]
			if '--dataFile' in sys.argv: dataFile = sys.argv[sys.argv.index('--dataFile') + 1]
			os.environ['DATASERVER_NO_REDIRECT'] = '1'
			server = ds_class( dataDir, dataFile )
		else:
			server = ds_class()

	logger.debug( 'Finished starting dataserver' )

	# TODO: Consider whether to use the global site manager as the registry,
	# or allow pyramid to hook zca. The latter should install a site manager
	# which is /beneath/ the global site manager, allowing for some degree
	# of separation still (I think). The pyramid.testing setup does
	# install a site manager, but fails to put it beneath the global site manager,
	# leading to some breakage in ZCA apis...this can be fixed by setting the site manager
	# to have a __bases__ that includes the global site manager.
	if pyramid_config is None:

		pyramid_config = pyramid.config.Configurator( registry=component.getGlobalSiteManager(),
													  debug_logger=logging.getLogger( 'pyramid' ),
													  settings=settings)

		pyramid_config.setup_registry()
		# Because we're using the global registry, the settings almost certainly
		# get trounced, so reinstall them
		pyramid_config.registry.settings.update( settings )

	# Our addons
	# First, ensure that each request is wrapped in default global transaction
	pyramid_config.include( 'pyramid_tm' )
	# ...which will veto commit on a 4xx or 5xx response
	pyramid_config.registry.settings['tm.commit_veto'] = 'pyramid_tm.default_commit_veto'
	pyramid_config.registry.settings['tm.attempts'] = 5
	# ...and which will retry a few times
	# NOTE: This is disabled because retry means that the entire request body must be
	# buffered, something that cannot happen with websockets. (However, the way the handlers
	# are set up, we may never get to the pyramid object on a websocket request, so
	# it probably doesn't matter. Verify).
	# TODO: This retry and transaction logic is very nice...how to integrate it with
	# the socketio_server and websocket handling? That all happens before we get down this
	# far
	#pyramid_config.registry.settings['tm.attempts'] = 3
	# Arrange for a db connection to be opened with each request
	# if pyramid_zodbconn.get_connection() is called (until called, this does nothing)
	pyramid_config.include( 'pyramid_zodbconn' )
	# Notice that we're using the db from the DS directly, not requiring construction
	# of a new DB based on a URI; that is a second option if we don't want the
	# DS object 'owning' the DB.
	# NOTE: It is not entirely clear how to get a connection to the dataserver if we're not
	# calling a method on the dataserver (and it doesn't have access to the request); however, it
	# is weird the way it is currently handled, with static fields of a context manager class.
	# I think the DS will want to be a transaction.interfaces.ISynchronizer and/or an IDataManager
	pyramid_config.registry.zodb_database = server.db # 0.2
	pyramid_config.registry._zodb_databases = { '': server.db } # 0.3
	#pyramid_config.registry.settings('zodbconn.uri') =

	pyramid_config.add_tween( 'nti.appserver.application.site_tween_factory', under='pyramid_tm.tm_tween_factory' )


	pyramid_config.include( 'pyramid_zcml' )

	# The pyramid_openid view requires a session. The repoze.who.plugins.openid plugin
	# uses a cookie by default to handle this, so it's not horrible to use an unencrypted
	# cookie session for this purpose. This keeps us from having to have a cross-server
	# solution.
	# NOTE: The OpenID store may be a bigger problem. Unless stateless actually works.
	# we have to make sure that file store is shared, or implement our own store.
	# Note: Stateless does seem to work.
	# Note: It's not clear how much benefit, if any, ropez.who.plugins.openid would bring
	# us. I don't know if I want 401s to automatically result in redirections to HTML pages.
	# OTOH, it would fit in with the existing place that we 'autocreate' users
	from pyramid.session import UnencryptedCookieSessionFactoryConfig
	my_session_factory = UnencryptedCookieSessionFactoryConfig('ntidataservercookiesecretpass')
	pyramid_config.set_session_factory( my_session_factory )

	pyramid_config.set_authorization_policy( pyramid.authorization.ACLAuthorizationPolicy() )
	pyramid_config.set_authentication_policy( pyramid_auth.create_authentication_policy() )

	pyramid_config.add_route( name='logon.ping', pattern='/dataserver2/logon.ping' )
	pyramid_config.add_route( name='logon.handshake', pattern='/dataserver2/logon.handshake' )
	pyramid_config.add_route( name='logon.nti.password', pattern='/dataserver2/logon.nti.password' )
	pyramid_config.add_route( name='logon.google', pattern='/dataserver2/logon.google' )
	pyramid_config.add_route( name='logon.google.result', pattern='/dataserver2/logon.google.result' )
	pyramid_config.add_route( name='logon.openid', pattern='/dataserver2/logon.openid' )
	pyramid_config.add_route( name='logon.logout', pattern='/dataserver2/logon.logout' )
	pyramid_config.add_route( name='logon.facebook.oauth1', pattern='/dataserver2/logon.facebook1' )
	pyramid_config.add_route( name='logon.facebook.oauth2', pattern='/dataserver2/logon.facebook2' )
	pyramid_config.scan( 'nti.appserver.logon' )
	# Deprecated logout alias
	pyramid_config.add_route( name='logout', pattern='/dataserver2/logout' )
	pyramid_config.add_view( route_name='logout', view='nti.appserver.logon.logout' )


	pyramid_config.add_route( name='verify_openid', pattern='/dataserver2/openid.html' )
	# Note that the openid value MUST be POST'd to this view; an unmodified view goes into
	# an infinite loop if the openid value is part of a GET param
	# This value works for any google apps account: https://www.google.com/accounts/o8/id
	pyramid_config.add_view( route_name='verify_openid', view='pyramid_openid.verify_openid' )
	pyramid_config.add_view( name='verify_openid', route_name='verify_openid', view='pyramid_openid.verify_openid' )


	import dataserver_socketio_views
	pyramid_config.add_route( name=dataserver_socketio_views.RT_HANDSHAKE, pattern=dataserver_socketio_views.URL_HANDSHAKE )
	pyramid_config.add_route( name=dataserver_socketio_views.RT_CONNECT, pattern=dataserver_socketio_views.URL_CONNECT )
	pyramid_config.scan( dataserver_socketio_views )

	# Temporarily make everyone an OU admin
	class OUAdminFactory(object):
		interface.implements( nti_interfaces.IGroupMember )
		component.adapts( object )

		def __init__( self, o ): pass

		@property
		def groups(self):
			return [ nti_interfaces.IPrincipal( "role:OU.Admin" ) ]
	pyramid_config.registry.registerAdapter( OUAdminFactory, name='OUAdminFactory' )


	if 'main_dictionary_path' in settings:
		try:
			dictionary = dictserver.dictionary.ChromeDictionary( settings['main_dictionary_path'] )
			pyramid_config.registry.registerUtility( dictionary )
			logger.debug( "Adding dictionary" )
			pyramid_config.load_zcml( 'pyramid.zcml' )
		except LookupError:
			logger.exception( "Failed to add dictionary server" )

	pyramid_config.add_renderer( name='rest', factory='nti.appserver.pyramid_renderers.REST' )

	indexmanager = None
	if create_ds:
		indexmanager = create_index_manager(server, use_whoosh_index_storage())

	if server:
		pyramid_config.registry.registerUtility( indexmanager, nti.contentsearch.interfaces.IIndexManager )
		pyramid_config.registry.registerUtility( server )
		if server.chatserver:
			pyramid_config.registry.registerUtility( server.chatserver )
	pyramid_config.registry.registerUtility( library )

	## Search
	# All the search views should accept an empty term (i.e., nothing after the trailing slash)
	# by NOT generating a 404 response but producing a 200 response with the same body
	# as if the term did not match anything. (This is what google does; the two alternatives
	# are to generate a 404--unfriendly and weird--or to treat it as a wildcard matching
	# everything--makes sense, but not scalable.)
	class _ContentSearchRootFactory(dict):
		__acl__ = ( (pyramid.security.Allow, pyramid.security.Authenticated, pyramid.security.ALL_PERMISSIONS), )

	for title in library.titles:
		indexname = os.path.basename( title.localPath )
		routename = 'search.book'
		if indexmanager and indexmanager.add_book(indexname=indexname, indexdir=os.path.join( title.localPath, 'indexdir')):
			pattern = '/' + indexname + '/Search/{term:.*}'
			name = routename + '.' + indexname
			pyramid_config.add_route( name=name, pattern=pattern, factory=_ContentSearchRootFactory )
			pyramid_config.add_view( route_name=name,
									 view='nti.contentsearch.pyramid_views.GetSearch',
									 renderer='rest',
									 permission=nauth.ACT_SEARCH )
			logger.debug( 'Added route %s to %s', name, pattern )

	# TODO: ACLs on searching: only the user should be allowed.
	class _UserSearchRootFactory(object):
		"""
		For searching the data of a particular user. We allow only
		that user to do so.
		"""
		def __init__( self, request ):
			# TODO: IPrincipals here
			self.__acl__ = ( (pyramid.security.Allow, request.matchdict['user'], pyramid.security.ALL_PERMISSIONS),
							 (pyramid.security.Deny,  pyramid.security.Everyone, pyramid.security.ALL_PERMISSIONS) )

	pyramid_config.add_route( name='search.user', pattern='/dataserver/users/{user}/Search/RecursiveUserGeneratedData/{term:.*}',
							  factory=_UserSearchRootFactory)
	pyramid_config.add_view( route_name='search.user',
							 view='nti.contentsearch.pyramid_views.UserSearch',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	pyramid_config.add_route( name='search.users', pattern='/dataserver/UserSearch/{term:.*}',
							  factory=_ContentSearchRootFactory)
	pyramid_config.add_view( route_name='search.users',
							 view='nti.appserver.dataserver_pyramid_views._UserSearchView',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	pyramid_config.add_route( name='search2.user', pattern='/dataserver2/users/{user}/Search/RecursiveUserGeneratedData/{term:.*}',
							  factory=_UserSearchRootFactory)
	pyramid_config.add_view( route_name='search2.user',
							 view='nti.contentsearch.pyramid_views.UserSearch',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	# Unified search for content and user data. It should follow the same
	# security policies for user data search
	pyramid_config.add_route( name='search2.unified', pattern='/dataserver2/users/{user}/Search/UnifiedSearch/{ntiid}/{term:.*}',
							  factory=_UserSearchRootFactory)
	pyramid_config.add_view( route_name='search2.unified',
							 view='nti.contentsearch.pyramid_views.Search',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	pyramid_config.add_route( name='search2.users', pattern='/dataserver2/UserSearch/{term:.*}',
							  factory=_ContentSearchRootFactory)
	pyramid_config.add_view( route_name='search2.users',
							 view='nti.appserver.dataserver_pyramid_views._UserSearchView',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	logger.debug( 'Finished creating search' )

	# User-generated data
	pyramid_config.add_route( name='user.pages.traversal', pattern='/dataserver2/users/{user}/Pages/{group}/UserGeneratedData{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.traversal', view='nti.appserver.dataserver_pyramid_views._UGDView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Recursive UGD
	pyramid_config.add_route( name='user.pages.recursivetraversal', pattern='/dataserver2/users/{user}/Pages/{group}/RecursiveUserGeneratedData{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.recursivetraversal', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Stream
	pyramid_config.add_route( name='user.pages.stream', pattern='/dataserver2/users/{user}/Pages/{group}/Stream{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.stream', view='nti.appserver.dataserver_pyramid_views._UGDStreamView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Recursive Stream
	pyramid_config.add_route( name='user.pages.recursivestream', pattern='/dataserver2/users/{user}/Pages/{group}/RecursiveStream{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.recursivestream', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDStreamView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# UGD and recursive stream
	pyramid_config.add_route( name='user.pages.ugdandrecursivestream', pattern='/dataserver2/users/{user}/Pages/{group}/UserGeneratedDataAndRecursiveStream{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.ugdandrecursivestream', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDStreamView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Service
	pyramid_config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._DSResource' )
	pyramid_config.add_view( route_name='user.root.service', view='nti.appserver.dataserver_pyramid_views._ServiceGetView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET'  )

	# UGD in OData style
	# Note: Objects should be parenthesized like this too.
	pyramid_config.add_route( name='user.pages.odata.traversal', pattern='/dataserver2/users/{user}/Pages({group:[^)/].*})/{type}{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/Pages/{group}/{type}'
							  )
	pyramid_config.add_view( route_name='user.pages.odata.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )


	# Top-level object traversal
	# TODO: This can probably be eliminated/combined with the
	# user.generic.traversal route, yes? And simply rely
	# on the context discriminators?
	pyramid_config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse',
							  factory='nti.appserver.dataserver_pyramid_views._DSResource' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._LibraryTOCRedirectView',
							 renderer='rest', context='nti.contentlibrary.interfaces.IContentUnit',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Generic user object tree traversal
	# For the Library/Main URL.
	# Gee it sure would be nice if the default (no-name) view would get used.
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', name='Main', context='nti.appserver.dataserver_pyramid_views._LibraryResource',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Modifying UGD
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest',
							 permission=nauth.ACT_DELETE, request_method='DELETE' )

	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EmptyContainerGetView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._NewContainerResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._UserResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._method_not_allowed',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._UserResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ProviderResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._provider_redirect_classes',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ProviderResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainerResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainerResource',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Modifying UGD beneath the Pages structure

	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._PagesResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._PagesResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._AbstractObjectResource',
							 permission=nauth.ACT_DELETE, request_method='DELETE' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._AbstractObjectResource',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )

	# attached resources
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._AbstractObjectResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='nti.dataserver.interfaces.ISimpleEnclosureContainer',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePutView',
							 renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosureDeleteView',
							 renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							 permission=nauth.ACT_UPDATE, request_method='DELETE' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Restore GET for the things we can POST enclosures to
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.appserver.dataserver_pyramid_views._AbstractObjectResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.dataserver.interfaces.ISimpleEnclosureContainer',
							 permission=nauth.ACT_READ, request_method='GET' )


	# Make 401 come back as appropriate. Otherwise we get 403
	# all the time, which prompts us to net send
	# credentials
	# TODO: Better use of an IChallangeDecider
	def forb_view(request):
		if 'repoze.who.identity' not in request.environ:
			result = hexc.HTTPUnauthorized()
			result.www_authenticate = ('Basic', 'realm="nti"')
			return result
		return request.exception
	pyramid_config.add_forbidden_view( forb_view )


	# register change listeners
	# Now, fork off the change listeners
	if create_ds:
		logger.info( 'Adding synchronous change listeners.' )
		server.add_change_listener( nti.dataserver.users.onChange )
		if indexmanager:
			server.add_change_listener( indexmanager.onChange )

		logger.info( 'Finished adding listeners' )


	# Our application needs to be innermost, before all the authkit stuff,
	# so we define this before that happens
	main = _Main( pyramid_config, http_port=http_port )
	#TODO: Tmp hacks
	main.addServeFiles( ('/Search/RecursiveUserGeneratedData/', 'contains') )
	main.addServeFiles( ('/dataserver/UserSearch/', None) )
	main.addServeFiles( ('/dataserver2', None) )

	application = main
	#application = pyramid_auth.wrap_repoze_middleware( application )

	return (application,main)

import geventwebsocket.handler

class AppServer(gevent.pywsgi.WSGIServer):
	def __init__( self, *args, **kwargs ):
		kwargs['handler_class'] = geventwebsocket.handler.WebSocketHandler
		super(AppServer,self).__init__(*args, **kwargs)

def use_whoosh_index_storage():
	return DATASERVER_WHOOSH_INDEXES

def create_index_manager(server, use_whosh_storage=None, user_indices_dir=None):

	if use_whosh_storage is None:
		use_whosh_storage = use_whoosh_index_storage()

	if use_whosh_storage:
		logger.debug( 'Creating Whoosh based index manager' )
		user_indices_dir = user_indices_dir or os.path.join( server._parentDir, 'indices' )
		ixman = nti.contentsearch.indexmanager.create_index_manager(user_indices_dir, dataserver=server)
	else:
		logger.debug( 'Creating Repoze-Catalog based index manager' )
		ixman = nti.contentsearch.indexmanager.create_repoze_index_manager(dataserver=server)

	#else:
	#	logger.debug( 'Creating ZEO based index manager' )
	#	indicesKey, blobsKey = '__indices', "__blobs"
	#	ixman = nti.contentsearch.indexmanager.create_zodb_index_manager(db = server.searchDB,
	#																	 indicesKey = indicesKey,
	#																	 blobsKey = blobsKey,
	#																	 dataserver = server)

	return ixman

# These two functions exist for the sake of the installed executables
# but they do nothing these days
def sharing_listener_main():
	pass

def index_listener_main():
	pass
