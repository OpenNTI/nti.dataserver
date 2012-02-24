#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

# XXX Import side-effects.
# Loading this file monkey-patches sockets and ssl to work with gevent.
# This is needed for the openid handling in logon.py, but doing it here is a bit
# earlier and has a greater chance of working. This is also after
# we have loaded ZODB and doesn't seem to interfere with it. See gunicorn.py.
# NOTE: 1.0 of gevent seems to fix the threading issue that cause problems with ZODB.
# Try to confirm that
import gevent
import gevent.monkey
if getattr( gevent, 'version_info', (0,) )[0] >= 1:
	logger.info( "Monkey patching most libraries for gevent" )
	# omit thread, it's required for multiprocessing futures, used in contentrendering
	gevent.monkey.patch_all(thread=False)
else:
	logger.info( "Monkey patching minimum libraries for gevent" )
	gevent.monkey.patch_socket(); gevent.monkey.patch_ssl()

import sys
import os
import traceback

import UserDict

import nti.dictserver.dictionary
import nti.dictserver._pyramid
dictserver = UserDict.UserDict()
dictserver.pyramid = nti.dictserver._pyramid
dictserver.dictionary = nti.dictserver.dictionary

from paste.exceptions.errormiddleware import ErrorMiddleware


import nti.dataserver as dataserver
 #Hmm, these next three MUST be imported. We seem to have a path-dependent import req.
import nti.dataserver.socketio_server
import nti.dataserver.wsgi
import nti.dataserver._Dataserver
import nti.dataserver.session_consumer
from nti.dataserver.library import Library
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
from nti.contentsearch.indexmanager import IndexManager
#from nti.contentsearch import indexmanager
contentsearch = nti.contentsearch

from selector import Selector

from nti.dataserver.users import SharingTarget
from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserver

from cors import CORSInjector

from zope import interface
from zope import component
from zope.configuration import xmlconfig
from zope.event import notify
from zope.processlifetime import ProcessStarting

import nti.appserver.workspaces

import pyramid.config
import pyramid.authorization
import pyramid.httpexceptions as hexc


import datetime
import pyramid_auth

from zope.location.location import LocationProxy

# Make the zope interface extend the pyramid interface
# Although this seems backward, it isn't. The zope location
# proxy implements the zope interface, and we want
# that to match with pyramid
from pyramid.interfaces import ILocation
from zope.location.interfaces import ILocation as IZLocation
IZLocation.__bases__ = (ILocation,)

from zope import container as zcontainer
from zope import location as zlocation


SOCKET_IO_PATH = 'socket.io'

#TDOD: we should do this as configuration
DATASERVER_ZEO_INDEXES = 'DATASERVER_NO_INDEX_BLOBS' not in os.environ
USE_FILE_INDICES = not DATASERVER_ZEO_INDEXES

class _Main(object):

	def __init__(self, app, pyramid_config, serveFiles=(), http_port=8080):
		self.captured = app
		self.serveFiles = [ ('/dictionary', None) ]
		self.http_port = http_port
		self.pyramid_config = pyramid_config
		self.pyramid_app = None

	def addServeFiles( self, serveFile ):
		self.serveFiles.append( serveFile )

	def setServeFiles( self, serveFiles=() ):
		self.serveFiles.extend( list(serveFiles) )

		for prefix, path  in serveFiles:
			self.pyramid_config.add_static_view( prefix, path, cache_max_age=datetime.timedelta(days=1) )
		self.pyramid_config.add_static_view( SOCKET_IO_PATH + '/static/', 'socketio:static/' )
		self.serveFiles.append( ( '/' + SOCKET_IO_PATH + '/static/', None ) )
		self.pyramid_app = self.pyramid_config.make_wsgi_app()

	def __call__(self, environ, start_request):

		# For CORS preflight requests, we must support the OPTIONS
		# method.
		# TODO: The OPTIONS method should be better implemented.
		if environ['REQUEST_METHOD'] == 'OPTIONS':
			start_request( '200 OK', [('Content-Type', 'text/plain')] )
			return [""]

		for prefix, _ in self.serveFiles:
			if _ == 'contains' and prefix in environ['PATH_INFO']: # tmp hack for user search
				return self.pyramid_app( environ, start_request )

			if environ['PATH_INFO'].startswith( prefix ):
				# pyramid handles the Range requests that are necessary to stream video,
				# but when the socket abruptly shuts down like it does on such requests,
				# a stack trace is logged by gevent.
				result = self.pyramid_app( environ, start_request )
				# NOTE: In the past, we looked for a cookie, ntifacesize, and also
				# query params for face. If the request was for prealgebra.css, we appended
				# CSS to make it match the face value "dynamically". This made rendering on the pad
				# faster. The pad now has a application.css that it likes to use.
				# If the content is not local, we should dynamically create one of those automatically.

				return result

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

		# TODO: socketio and authentication? The SocketIOHandler
		# class runs and deals completely with the socket.io path before
		# any of our application code runs, including authkit.
		# So these URLs are effectively not authenticated unless we do it
		# manually. (We could also subclass SocketIOHandler)
		if environ['PATH_INFO'].startswith( '/' + SOCKET_IO_PATH ):
			if 'wsgi.websocket' not in environ:
				# Well damn. We failed to upgrade the connection to a websocket.
				# This usually means that we are behind a proxy that doesn't
				# support websockets, which is most annoying. Best we can do is return 404
				# (if we don't do this here, then the return below causes problems since
				# we don't actually spin in a greenlet)
				start_request( '404 Not Found', [('Content-Type', 'text/plain')] )
				return ['WebSockets not found']

			# Because we're going to sit here in a greenlet spinning in
			# our sleep, we need to close the transaction. (It's not
			# like we're authenticating). We would want to re-obtain it
			# when needed.
			environ['app.db.connection'].transaction_manager.commit()
			environ['app.db.connection'].close()
			environ['socketio'].session.wsgi_app_greenlet = True
			return

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

		try:
			return self.captured( environ, start_request )
		except hexc.HTTPError as h:
			start_request( h.status, h.headers.items(), sys.exc_info() )
			return [h.message]

def createApplication( http_port,
					   library,
					   process_args=False,
					   create_ds=True,
					   pyramid_config=None,
					   sync_changes=False,
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
		ds_class = dataserver._Dataserver.Dataserver if not sync_changes else dataserver._Dataserver._SynchronousChangeDataserver
		if process_args:
			dataDir = "~/tmp"
			dataFile = "test.fs"
			if '--dataDir' in sys.argv: dataDir = sys.argv[sys.argv.index('--dataDir') + 1]
			if '--dataFile' in sys.argv: dataFile = sys.argv[sys.argv.index('--dataFile') + 1]
			os.environ['DATASERVER_NO_REDIRECT'] = '1'
			server = ds_class( dataDir, dataFile )
		else:
			server = ds_class()

	user_indices_dir = os.path.join( server._parentDir, 'indices' )

	logger.debug( 'Finished starting dataserver' )


	userTree = dataserver.wsgi.UserTree( server, library )
	quizTree = dataserver.wsgi.QuizTree( server )
	libraryTree = dataserver.wsgi.LibraryTree( library )
	logger.debug( 'Finished creating trees' )

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
	pyramid_config.add_route( name='logout', pattern='/dataserver2/logout' )
	pyramid_config.add_view( route_name='logout', view='nti.appserver.dataserver_pyramid_views._logout' )

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

	pyramid_config.add_route( name='verify_openid', pattern='/dataserver2/openid.html' )
	# Note that the openid value MUST be POST'd to this view; an unmodified view goes into
	# an infinite loop if the openid value is part of a GET param
	# This value works for any google apps account: https://www.google.com/accounts/o8/id
	pyramid_config.add_view( route_name='verify_openid', view='pyramid_openid.verify_openid' )
	pyramid_config.add_view( name='verify_openid', route_name='verify_openid', view='pyramid_openid.verify_openid' )


	# Temporarily make everyone an OU admin
	class OUAdminFactory(object):
		interface.implements( nti_interfaces.IGroupMember )
		component.adapts( object )

		def __init__( self, o ): pass

		@property
		def groups(self):
			return [ nti_interfaces.IPrincipal( "role:OU.Admin" ) ]
	pyramid_config.registry.registerAdapter( OUAdminFactory, name='OUAdminFactory' )


	selector = Selector( consume_path=False )
	if dictserver.pyramid and 'main_dictionary_path' in settings:
		try:
			dictionary = dictserver.dictionary.ChromeDictionary( settings['main_dictionary_path'] )
			pyramid_config.registry.registerUtility( dictionary )
			logger.debug( "Adding dictionary" )

			pyramid_config.add_static_view( '/dictionary/static', 'nti.dictserver:static/',
											cache_max_age=datetime.timedelta(days=1) )
			pyramid_config.add_route( name='dictionary.word', pattern='/dictionary/{word}',
									  request_method='GET')
			pyramid_config.scan( dictserver.pyramid )
		except LookupError:
			logger.exception( "Failed to add dictionary server" )

	pyramid_config.add_renderer( name='rest', factory='nti.appserver.pyramid_renderers.REST' )

	indexmanager = None
	if create_ds:
		indexmanager = create_index_manager(server, use_zeodb_index_storage(), user_indices_dir)

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
		if indexmanager and indexmanager.add_book( os.path.join( title.localPath, 'indexdir' ), indexname ):
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

	pyramid_config.add_route( name='search2.users', pattern='/dataserver2/UserSearch/{term:.*}',
							  factory=_ContentSearchRootFactory)
	pyramid_config.add_view( route_name='search2.users',
							 view='nti.appserver.dataserver_pyramid_views._UserSearchView',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	logger.debug( 'Finished creating search' )

	userTree.addToSelector( selector )
	quizTree.addToSelector( selector )
	libraryTree.addToSelector( selector )
	logger.debug( 'Finished adding trees' )


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
							 renderer='rest', context='nti.dataserver.interfaces.ILibraryTOCEntry',
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


	# register change listeners
	# Now, fork off the change listeners
	if create_ds:
		if sync_changes:
			logger.info( 'Adding synchronous change listeners.' )
			server.add_change_listener( SharingTarget.onChange )
			server.add_change_listener( IndexManager.onChange )
		else:
			logger.info( "Change listeners should already be running." )

		logger.info( 'Finished adding listeners' )


	# Our application needs to be innermost, before all the authkit stuff,
	# so we define this before that happens
	main = _Main( selector, pyramid_config, http_port=http_port )
	#TODO: Tmp hacks
	main.addServeFiles( ('/Search/RecursiveUserGeneratedData/', 'contains') )
	main.addServeFiles( ('/dataserver/UserSearch/', None) )
	main.addServeFiles( ('/dataserver2', None) )

	application = main
	application = pyramid_auth.wrap_repoze_middleware( application )

	return (application,main)

class AppServer(dataserver.socketio_server.SocketIOServer):
	def _after_create_session( self, session, environ=None ):
		# Try to extract the authenticated username, if we can. We don't have
		# a pyramid request to draw on, though
		username = None
		identity = None
		auth_policy = None
		if environ:
			# A pyramid_auth.NTIAuthenticationPolicy
			auth_policy = component.getUtility( pyramid.interfaces.IAuthenticationPolicy )
			api = auth_policy.api_factory( environ )
			identity = api.authenticate()
			if identity:
				username = identity['repoze.who.userid']
		logger.debug( "Creating session handler for '%s'/%s using %s and %s", username, dict(identity) if identity else None, auth_policy, environ )
		session.message_handler = dataserver.session_consumer.SessionConsumer(username=username,session=session)

def _configure_logging():
	# TODO: Where should logging in these background processes be configured?
	logging.basicConfig( level=logging.INFO )
	logging.getLogger( 'nti' ).setLevel( logging.DEBUG )
	logging.root.handlers[0].setFormatter( logging.Formatter( '%(asctime)s [%(name)s] %(levelname)s: %(message)s' ) )

def _add_sharing_listener( server ):
	_configure_logging()
	print 'Adding sharing listener', os.getpid(), server
	server.add_change_listener( SharingTarget.onChange )


def use_zeodb_index_storage():
	return not USE_FILE_INDICES

def _add_index_listener( server, user_indices_dir ):
	_configure_logging()
	print 'Adding index listener', os.getpid(), dataserver
	create_index_manager(server, use_zeodb_index_storage(), user_indices_dir)
	server.add_change_listener( IndexManager.onChange )

def create_index_manager(server, use_zeo_storage=None, user_indices_dir='/tmp'):

	if use_zeo_storage is None:
		use_zeo_storage = use_zeodb_index_storage()

	if use_zeo_storage:
		logger.debug( 'Creating ZEO index manager' )
		indicesKey, blobsKey = '__indices', "__blobs"
		ixman = nti.contentsearch.indexmanager.create_zodb_index_manager(db = server.searchDB,
																		 indicesKey = indicesKey,
																		 blobsKey = blobsKey,
																		 dataserver = server)
	else:
		with server.dbTrans():
			usernames = [name for name in server.root['users'].keys()]
			ixman = nti.contentsearch.indexmanager.create_index_manager(user_indices_dir, usernames)

	return ixman

def sharing_listener_main():
	_configure_logging()
	dataserver._Dataserver.temp_env_run_change_listener( _add_sharing_listener )

def index_listener_main():
	_configure_logging()
	dataserver._Dataserver.temp_env_run_change_listener( _add_index_listener, None )
