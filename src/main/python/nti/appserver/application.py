#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

import sys
import os
import traceback

import UserDict


try:
	import nti.dictserver._pyramid
	dictserver = UserDict.UserDict()
	dictserver.pyramid = nti.dictserver._pyramid
except (ImportError,LookupError):
	logger.exception( "Dictionary lookups unavailable." )
	dictserver = UserDict.UserDict()
	dictserver.pyramid = None

from paste.exceptions.errormiddleware import ErrorMiddleware


import nti.dataserver as dataserver
import nti.dataserver.wsgi #Hmm, this MUST be imported. We seem to have a path-dependent import req.
from nti.dataserver.library import Library

import nti.contentsearch
from nti.contentsearch import IndexManager
contentsearch = nti.contentsearch

from selector import Selector

from nti.dataserver.users import SharingTarget

from cors import CORSInjector
import auth
from layers import register_implicit_layers

from zope import component
from zope.configuration import xmlconfig

from . import workspaces

import pyramid.config
import pyramid.authorization
import pyramid.httpexceptions as hexc
import datetime
import pyramid_auth

import warnings
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
USE_FILE_INDICES = 'USE_ZEO_USER_INDICES' not in os.environ

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

			# Because we're going to sit here in a greenlet spinning in
			# our sleep, we need to close the transaction. (It's not
			# like we're authenticating). We would want to re-obtain it
			# when needed.
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
			start_request( '200 OK', (('Content-Type', 'text/plain'),) )
			return body + '\n'

		return self.captured( environ, start_request )

def createApplication( http_port, library, process_args=False, create_ds=True ):
	server = None
	register_implicit_layers()
	logger.debug( 'Began starting dataserver' )
	server = None
	if not create_ds:
		class MockServer(object):
			pass
		server = MockServer()
		server._parentDir = '.'
		server._dataFileName = 'data.fs'
	else:
		if process_args:
			dataDir = "~/tmp"
			dataFile = "test.fs"
			if '--dataDir' in sys.argv: dataDir = sys.argv[sys.argv.index('--dataDir') + 1]
			if '--dataFile' in sys.argv: dataFile = sys.argv[sys.argv.index('--dataFile') + 1]
			os.environ['DATASERVER_NO_REDIRECT'] = '1'
			server = dataserver.Dataserver( dataDir, dataFile )
		else:
			server = dataserver.Dataserver()

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
	pyramid_config = pyramid.config.Configurator( registry=component.getGlobalSiteManager(),
												  debug_logger=logging.getLogger( 'pyramid' ),
												  exceptionresponse_view=pyramid_auth.exceptionresponse_view)
	pyramid_config.setup_registry()
	# Note that we are using an exception-catching view to convert
	# forbidden responses into 401 responses. This is slightly odd
	pyramid_config.set_authentication_policy( pyramid_auth.NTIBasicAuthPolicy() )
	pyramid_config.set_authorization_policy( pyramid.authorization.ACLAuthorizationPolicy() )
	pyramid_config.add_view( pyramid_auth.exceptionresponse_view, context=hexc.HTTPForbidden )

	xmlconfig.file( 'configure.zcml', package=nti.appserver )


	selector = Selector( consume_path=False )
	if dictserver.pyramid:
		logger.debug( "Adding dictionary" )
		pyramid_config.add_static_view( '/dictionary/static', 'nti.dictserver:static/',
										cache_max_age=datetime.timedelta(days=1) )
		pyramid_config.add_route( name='dictionary.word', pattern='/dictionary/{word}',
								  request_method='GET')
		pyramid_config.scan( dictserver.pyramid )

	pyramid_config.add_renderer( name='rest', factory='nti.appserver.pyramid_renderers.REST' )

	indexmanager = None
	if create_ds:
		indexmanager = create_index_manager(server, use_zeodb_index_storage(), user_indices_dir)
	class SearchFactory(dict):
		__acl__ = ( (pyramid.security.Allow, pyramid.security.Authenticated, pyramid.security.ALL_PERMISSIONS), )

	if create_ds:
		pyramid_config.registry.registerUtility( indexmanager, nti.contentsearch.IIndexManager )
		pyramid_config.registry.registerUtility( server )
	pyramid_config.registry.registerUtility( library )
	for title in library.titles:
		indexname = os.path.basename( title.localPath )
		routename = 'search.book'
		if indexmanager and indexmanager.add_book( os.path.join( title.localPath, 'indexdir' ), indexname ):
			pattern = '/' + indexname + '/Search/{term}'
			name = routename + '.' + indexname
			pyramid_config.add_route( name=name, pattern=pattern, factory=SearchFactory )
			pyramid_config.add_view( route_name=name,
									 view='nti.contentsearch.pyramid_views.GetSearch',
									 renderer='rest',
									 permission='search' )
			logger.debug( 'Added route %s to %s', name, pattern )

	pyramid_config.add_route( name='search.user', pattern='/dataserver/users/{user}/Search/RecursiveUserGeneratedData/{term}',
							  factory=SearchFactory)
	pyramid_config.add_view( route_name='search.user',
							 view='nti.contentsearch.pyramid_views.UserSearch',
							 renderer='rest',
							 permission='search')

	pyramid_config.add_route( name='search.users', pattern='/dataserver/UserSearch/{term:.*}',
							  factory=SearchFactory)
	pyramid_config.add_view( route_name='search.users',
							 view='nti.appserver.dataserver_pyramid_views._UserSearchView',
							 renderer='rest',
							 permission='search')

	logger.debug( 'Finished creating search' )

	userTree.addToSelector( selector )
	quizTree.addToSelector( selector )
	libraryTree.addToSelector( selector )
	logger.debug( 'Finished adding trees' )

	# UGD in OData style
	# Note: Objects should be parenthesized like this too.
	pyramid_config.add_route( name='user.pages.odata.traversal', pattern='/dataserver2/users/{user}/Pages({group:[^)/].*})/{type}{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/Pages/{group}/{type}'
							  )
	pyramid_config.add_view( route_name='user.pages.odata.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 name='', renderer='rest',
							 permission='read', request_method='GET' )


	# User-generated data
	pyramid_config.add_route( name='user.pages.traversal', pattern='/dataserver2/users/{user}/Pages/{group}/UserGeneratedData{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.traversal', view='nti.appserver.dataserver_pyramid_views._UGDView',
							 name='', renderer='rest',
							 permission='read', request_method='GET' )

	# Recursive UGD
	pyramid_config.add_route( name='user.pages.recursivetraversal', pattern='/dataserver2/users/{user}/Pages/{group}/RecursiveUserGeneratedData{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.recursivetraversal', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDView',
							 name='', renderer='rest',
							 permission='read', request_method='GET' )

	# Stream
	pyramid_config.add_route( name='user.pages.stream', pattern='/dataserver2/users/{user}/Pages/{group}/Stream{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.stream', view='nti.appserver.dataserver_pyramid_views._UGDStreamView',
							 name='', renderer='rest',
							 permission='read', request_method='GET' )

	# Recursive Stream
	pyramid_config.add_route( name='user.pages.recursivestream', pattern='/dataserver2/users/{user}/Pages/{group}/RecursiveStream{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.recursivestream', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDStreamView',
							 name='', renderer='rest',
							 permission='read', request_method='GET' )

	# UGD and recursive stream
	pyramid_config.add_route( name='user.pages.ugdandrecursivestream', pattern='/dataserver2/users/{user}/Pages/{group}/UserGeneratedDataAndRecursiveStream{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.ugdandrecursivestream', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDStreamView',
							 name='', renderer='rest',
							 permission='read', request_method='GET' )

	# Service
	pyramid_config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}',
							  factory='nti.appserver.dataserver_pyramid_views._DSResource' )
	pyramid_config.add_view( route_name='user.root.service', view='nti.appserver.dataserver_pyramid_views._ServiceGetView',
							 name='', renderer='rest',
							 permission='read', request_method='GET'  )

	# Top-level object traversal
	# TODO: This can probably be eliminated/combined with the
	# user.generic.traversal route, yes? And simply rely
	# on the context discriminators?
	pyramid_config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse',
							  factory='nti.appserver.dataserver_pyramid_views._DSResource' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',
							 permission='read', request_method='GET' )

	# Generic user object tree traversal
	pyramid_config.add_route( name='user.generic.traversal', pattern='/dataserver2/users/*traverse',
							  factory='nti.appserver.dataserver_pyramid_views._UsersRootResource' )
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',
							 permission='read', request_method='GET' )
	# For the Library/Main URL.
	# Gee it sure would be nice if the default (no-name) view would get used.
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', name='Main',
							 permission='read', request_method='GET' )

	# Modifying UGD
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest',
							 permission='delete', request_method='DELETE' )
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EmptyContainerGetView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._NewContainerResource',
							 permission='read', request_method='GET' )
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._UserResource',
							 permission='create', request_method='POST' )
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='edit', request_method='PUT' )
	# Modifying UGD beneath the Pages structure

	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._PagesResource',
							 permission='create', request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._PagesResource',
							 permission='read', request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='delete', request_method='DELETE' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='edit', request_method='PUT' )

	# attached resources
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='create', request_method='POST' )
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePutView',
							 renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							 permission='edit', request_method='PUT' )
	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							 permission='read', request_method='GET' )


	pyramid_config.add_view( route_name='user.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='read', request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='read', request_method='GET' )

	# Providers tree.
	# TODO: Unify this, don't want to duplicate everything from
	# user tree.
	pyramid_config.add_route( name='provider.generic.traversal', pattern='/dataserver2/providers/*traverse',
							  factory='nti.appserver.dataserver_pyramid_views._ProvidersRootResource' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',
							 permission='read', request_method='GET' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest',
							 permission='read', request_method='DELETE' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EmptyContainerGetView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._NewContainerResource',
							 permission='read', request_method='GET' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._UserResource',
							 permission='create', request_method='POST' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='edit', request_method='PUT' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.appserver.dataserver_pyramid_views._ContainedObjectResource',
							 permission='read', request_method='GET' )

	# Attached resources
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='nti.dataserver.interfaces.ISimpleEnclosureContainer',
							 permission='create', request_method='POST' )
	pyramid_config.add_view( route_name='provider.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePutView',
							 renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							 permission='edit', request_method='PUT' )


	# register change listeners
	# Now, fork off the change listeners
	if create_ds:
		dataserver.spawn_change_listener( server, _add_sharing_listener )
		dataserver.spawn_change_listener( server, _add_index_listener, (user_indices_dir,) )
		logger.info( 'Finished adding listeners' )


	# Our application needs to be innermost, before all the authkit stuff,
	# so we define this before that happens
	main = _Main( selector, pyramid_config, http_port=http_port )
	#TODO: Tmp hacks
	main.addServeFiles( ('/Search/RecursiveUserGeneratedData/', 'contains') )
	main.addServeFiles( ('/dataserver/UserSearch/', None) )
	main.addServeFiles( ('/dataserver2', None) )

	application = auth.add_authentication( main, server )
	application = ErrorMiddleware( application, show_exceptions_in_wsgi_errors=True, debug=True )
	# CORS needs to be outermost so that even 401 errors ond
	# exceptions have the chance to get their responses wrapped
	application = CORSInjector( application )

	return (application,main)

class AppServer(dataserver.socketio_server.SocketIOServer):
	def _after_create_session( self, session ):
		session.message_handler = dataserver.session_consumer.SessionConsumer()

def _configure_logging():
	# TODO: Where should logging in these background processes be configured?
	logging.basicConfig( level=logging.DEBUG )
	logging.getLogger( 'nti' ).setLevel( logging.DEBUG )
	logging.root.handlers[0].setFormatter( logging.Formatter( '[%(name)s] %(levelname)s: %(message)s' ) )


def _add_sharing_listener( server ):
	_configure_logging()

	print 'Adding sharing listener', os.getpid(), server
	register_implicit_layers()
	server.add_change_listener( SharingTarget.onChange )


def use_zeodb_index_storage():
	return not USE_FILE_INDICES

def _add_index_listener( server, user_indices_dir ):
	_configure_logging()
	print 'Adding index listener', os.getpid(), dataserver
	create_index_manager(server, use_zeodb_index_storage(), user_indices_dir)
	server.add_change_listener( IndexManager.onChange )

def create_index_manager(server, use_zeo_storage=False, user_indices_dir='/tmp'):

	if use_zeo_storage:
		indicesKey, blobsKey = '__indices', "__blobs"
		indexmanager = contentsearch.create_zodb_index_manager(	db=server.searchDB,
																indicesKey=indicesKey,
																blobsKey=blobsKey)
	else:
		with server.dbTrans():
			usernames = [name for name in server.root['users'].keys()]
			indexmanager = contentsearch.create_index_manager(user_indices_dir, usernames)

	return indexmanager

