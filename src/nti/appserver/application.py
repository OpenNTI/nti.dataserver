#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

$Id$
"""
import logging
logger = logging.getLogger( __name__ )

# Import this first to ensure gevent is monkey patched
import nti.dataserver as dataserver

import gevent.local

import sys
import os
import simplejson

import nti.dictserver as dictserver
import nti.dictserver.dictionary


import nti.dataserver._Dataserver

from nti.dataserver import interfaces as nti_interfaces
from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentfragments import interfaces as cfg_interfaces

import nti.contentsearch
import nti.contentsearch.indexmanager

import nti.dataserver.users
from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserver

from zope import interface
from zope import component
from zope.configuration import xmlconfig
from zope.event import notify
from zope.processlifetime import ProcessStarting

# Make sure our thread-local monkey patch has been applied
from zope.component.hooks import siteinfo
assert gevent.local.local in type(siteinfo).__bases__

import zope.interface.exceptions

import pyramid.config
import pyramid.authorization
import pyramid.security
import pyramid.httpexceptions as hexc


import nti.appserver.workspaces
from nti.appserver import pyramid_auth
from nti.appserver import interfaces as app_interfaces
from nti.appserver.traversal import ZopeResourceTreeTraverser
from nti.appserver import pyramid_authorization


# Make the zope interface extend the pyramid interface
# Although this seems backward, it isn't. The zope location
# proxy implements the zope interface, and we want
# that to match with pyramid
from pyramid.interfaces import ILocation
from zope.location.interfaces import ILocation as IZLocation
IZLocation.__bases__ = (ILocation,)


SOCKET_IO_PATH = 'socket.io'




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
		return self.pyramid_app( environ, start_request )

def _create_xml_conf_machine( settings ):
	xml_conf_machine = xmlconfig.ConfigurationMachine()
	xmlconfig.registerCommonDirectives( xml_conf_machine )
	if 'devmode' in settings and settings['devmode']:
		logger.debug( "Enabling devmode" )
		xml_conf_machine.provideFeature( 'devmode' )
	return xml_conf_machine

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
	try:
		xml_conf_machine = _create_xml_conf_machine( settings )
		xml_conf_machine = xmlconfig.file( 'configure.zcml', package=nti.appserver, context=xml_conf_machine )
		if 'site_zcml' in settings:
			logger.debug( "Loading site settings from %s", settings['site_zcml'] )
			xml_conf_machine = xmlconfig.file( settings['site_zcml'],  package=nti.appserver, context=xml_conf_machine )
			# Preserve the conf machine so that when we load other files later any
			# exclude settings get processed
	except Exception:
		logger.exception( "Failed to load config. Settings: %s", settings )
		raise

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
		ds_class = dataserver._Dataserver.Dataserver if not callable(create_ds) else create_ds
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
													  package=nti.appserver,
													  settings=settings)
		# Note that because we're using the global registre, the Configurator doesn't
		# set it up. So all the arguments it would pass we must pass.
		# If we fail to do this, things like 'pyramid.includes' don't get processed
		pyramid_config.setup_registry(debug_logger=logging.getLogger( 'pyramid' ),
									  settings=settings)


	# Our addons
	# First, ensure that each request is wrapped in default global transaction
	pyramid_config.include( 'pyramid_tm' )
	# ...which will veto commit on a 4xx or 5xx response
	pyramid_config.registry.settings['tm.commit_veto'] = 'pyramid_tm.default_commit_veto'
	# ...and which will retry a few times. Note this requires the request to be fully buffered
	pyramid_config.registry.settings['tm.attempts'] = 5

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

	# Add a tween that ensures we are within a SiteManager. This also has
	# some logic to clean up some bad transaction handling in pyramid_tm.
	pyramid_config.add_tween( 'nti.appserver.zope_site_tween.site_tween_factory', under='pyramid_tm.tm_tween_factory' )


	pyramid_config.include( 'pyramid_zcml' )
	import pyramid_zcml
	# make it respect the features we choose to provide
	pyramid_zcml.ConfigurationMachine = lambda: _create_xml_conf_machine( settings )

	# Our traversers
	# TODO: Does doing this get us into any trouble with a non-matching request.resource_url
	# method? Do we need to install an implementation if IResourceURL?
	# http://docs.pylonsproject.org/projects/pyramid/en/1.3-branch/narr/hooks.html#changing-how-pyramid-request-request-resource-url-generates-a-url
	pyramid_config.add_traverser( ZopeResourceTreeTraverser )

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

	pyramid_config.set_authorization_policy( pyramid_authorization.ACLAuthorizationPolicy() )
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
			dictionary = dictserver.dictionary.SQLiteJsonDictionary( settings['main_dictionary_path'] )
			pyramid_config.registry.registerUtility( dictionary )
			logger.debug( "Adding dictionary" )
		except Exception:
			logger.exception( "Failed to add dictionary server" )

	pyramid_config.load_zcml( 'nti.appserver:pyramid.zcml' ) # must use full spec, we may not have created the pyramid_config
	pyramid_config.add_renderer( name='rest', factory='nti.appserver.pyramid_renderers.REST' )
	# Override the stock Chameleon template renderer to use z3c.pt for better compatibility with
	# the existing Zope stuff
	pyramid_config.add_renderer( name='.pt', factory='nti.appserver.z3c_zpt.renderer_factory' )

	indexmanager = None
	if create_ds:
		# This may be excluded by a previous setting in site.zcml, and replaced with something else
		xml_conf_machine = xmlconfig.file( 'configure_indexmanager.zcml',  package=nti.appserver, context=xml_conf_machine )

	indexmanager = component.queryUtility( nti.contentsearch.interfaces.IIndexManager )

	if server:
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

	@interface.implementer( app_interfaces.IFileQuestionMap )
	class _QuestionMap(dict):

		def __init__( self ):
			super(_QuestionMap,self).__init__()
			self.by_file = {}

		def _from_index_entry(self, index, dirname=None):
			filename = None
			if index.get( 'filename' ):
				filename = os.path.join( dirname, index.get( 'filename' ) ) if dirname else index['filename']
			for item in index['Items'].values():
				for k, v in item['AssessmentItems'].items():
					__traceback_info__ = k, v

					factory = nti.externalization.internalization.find_factory_for( v )
					assert factory is not None
					obj = factory()
					nti.externalization.internalization.update_from_external_object( obj, v, require_updater=True )
					obj.ntiid = k
					if filename:
						self.by_file.setdefault( filename, [] ).append( obj )
						# Hack in ACL support. We are piggybacking off of
						# IDelimitedEntry's support in authorization_acl.py
						def read_contents_of_sibling_entry( sibling_name ):
							try:
								return open( os.path.join( os.path.dirname( filename ), sibling_name ), 'r' ).read()
							except (OSError,IOError):
								return None

						obj.filename = filename
						obj.read_contents_of_sibling_entry = read_contents_of_sibling_entry
						interface.alsoProvides( obj, lib_interfaces.IFilesystemEntry )

					self[k] = obj
				if 'Items' in item:
					self._from_index_entry( item, dirname=dirname )


	question_map = _QuestionMap()
	pyramid_config.registry.registerUtility( question_map, app_interfaces.IFileQuestionMap )
	for title in library.titles:
		asm_index_text = title.read_contents_of_sibling_entry( 'assessment_index.json' )
		if asm_index_text:
			asm_index_text = unicode(asm_index_text)
			# In this one specific case, we know that these are already
			# content fragments (probably HTML content fragments)
			# If we go through the normal adapter process from string to
			# fragment, we will wind up with sanitized HTML, which is not what
			# we want, in this case
			# TODO: Needs specific test cases
			def hook(o):
				return dict( (k,cfg_interfaces.UnicodeContentFragment(v) if isinstance(v, unicode) else v) for k, v in o )

			index = simplejson.loads( asm_index_text,
									  object_pairs_hook=hook )
			try:
				question_map._from_index_entry( index, dirname=getattr(title, 'localPath', None) )
			except (zope.interface.exceptions.Invalid, ValueError):
				# Because the map is updated in place, depending on where the error
				# was, we might have some data...that's not good, but it's not a show stopper either,
				# since we shouldn't get content like this out of the rendering process
				logger.exception( "Failed to load assessment items, invalid assessment_index for %s", title )

		# FIXME: This fails for non-local content. Need caching of indexes
		try:
			indexname = os.path.basename( title.localPath )
			routename = 'search.book'

			indexdir = os.path.join( title.localPath, 'indexdir' )
			__traceback_info__ = indexdir
			if indexmanager and indexmanager.add_book(indexname=indexname, indexdir=os.path.join( title.localPath, 'indexdir')):
				pattern = '/' + indexname + '/Search/{term:.*}'
				name = routename + '.' + indexname
				pyramid_config.add_route( name=name, pattern=pattern, factory=_ContentSearchRootFactory )
				pyramid_config.add_view( route_name=name,
										 view='nti.contentsearch.pyramid_views.GetSearch',
										 renderer='rest',
										 permission=nauth.ACT_SEARCH )
				logger.debug( 'Added route %s to %s', name, pattern )
		except AttributeError:
			# Temp hack while these things do not have local paths
			logger.debug( "Failed to add book search entry" )
		except ImportError:
			# Adding a book on disk loads the Whoosh indexes, which
			# are implemented as pickles. Incompatible version changes
			# lead to unloadable pickles. We've seen this manifest as ImportError
			logger.exception( "Failed to add book search %s", title )

	# TODO: ACLs on searching: only the user should be allowed.
	@interface.implementer(ILocation)
	class _UserSearchRootFactory(object):
		"""
		For searching the data of a particular user. We allow only
		that user to do so.
		"""
		__name__ = 'UserSearch'
		__parent__ = None
		def __init__( self, request ):
			self.__parent__ = request.registry.getUtility( nti_interfaces.IDataserver ).root
			# TODO: IPrincipals here
			self.__acl__ = ( (pyramid.security.Allow, request.matchdict['user'], pyramid.security.ALL_PERMISSIONS),
							 (pyramid.security.Deny,  pyramid.security.Everyone, pyramid.security.ALL_PERMISSIONS) )

	pyramid_config.add_route( name='search.user', pattern='/dataserver2/users/{user}/Search/RecursiveUserGeneratedData/{term:.*}',
							  factory=_UserSearchRootFactory)
	pyramid_config.add_view( route_name='search.user',
							 view='nti.contentsearch.pyramid_views.UserSearch',
							 renderer='rest',
							 permission=nauth.ACT_SEARCH)

	pyramid_config.add_route( name='search.users', pattern='/dataserver2/UserSearch/{term:.*}',
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
							  factory='nti.appserver._dataserver_pyramid_traversal.users_root_resource_factory',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.traversal', view='nti.appserver.dataserver_pyramid_views._UGDView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Recursive UGD
	pyramid_config.add_route( name='user.pages.recursivetraversal', pattern='/dataserver2/users/{user}/Pages/{group}/RecursiveUserGeneratedData{_:/?}',
							  factory='nti.appserver._dataserver_pyramid_traversal.users_root_resource_factory',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.recursivetraversal', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Stream
	pyramid_config.add_route( name='user.pages.stream', pattern='/dataserver2/users/{user}/Pages/{group}/Stream{_:/?}',
							  factory='nti.appserver._dataserver_pyramid_traversal.users_root_resource_factory',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.stream', view='nti.appserver.dataserver_pyramid_views._UGDStreamView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Recursive Stream
	pyramid_config.add_route( name='user.pages.recursivestream', pattern='/dataserver2/users/{user}/Pages/{group}/RecursiveStream{_:/?}',
							  factory='nti.appserver._dataserver_pyramid_traversal.users_root_resource_factory',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.recursivestream', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDStreamView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )

	# UGD and recursive stream
	pyramid_config.add_route( name='user.pages.ugdandrecursivestream', pattern='/dataserver2/users/{user}/Pages/{group}/UserGeneratedDataAndRecursiveStream{_:/?}',
							  factory='nti.appserver._dataserver_pyramid_traversal.users_root_resource_factory',
							  traverse='/{user}/{group}'
							  )
	pyramid_config.add_view( route_name='user.pages.ugdandrecursivestream', view='nti.appserver.dataserver_pyramid_views._RecursiveUGDStreamView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )



	# Service
	pyramid_config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}',
							  #factory='nti.appserver.dataserver_pyramid_views._DSResource' )
							  factory='nti.appserver._dataserver_pyramid_traversal.dataserver2_root_resource_factory' )
	pyramid_config.add_view( route_name='user.root.service', view='nti.appserver.dataserver_pyramid_views._ServiceGetView',
							 name='', renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET'  )

	# UGD in OData style
	# Note: Objects should be parenthesized like this too.
	pyramid_config.add_route( name='user.pages.odata.traversal', pattern='/dataserver2/users/{user}/Pages({group:[^)/].*})/{type}{_:/?}',
							  factory='nti.appserver._dataserver_pyramid_traversal.users_root_resource_factory',
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
							  #factory='nti.appserver.dataserver_pyramid_views._DSResource' )
							  factory='nti.appserver._dataserver_pyramid_traversal.dataserver2_root_resource_factory' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.scan( 'nti.appserver.contentlibrary_views' )
	pyramid_config.scan( 'nti.appserver.liking_views' )
	pyramid_config.scan( 'nti.appserver.flagging_views' )
	pyramid_config.scan( 'nti.appserver._hacks' )

	# Generic user object tree traversal
	# For the Library/Main URL.
	# Gee it sure would be nice if the default (no-name) view would get used.
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', name='Main', context='nti.contentlibrary.interfaces.IContentPackageLibrary',
							 permission=nauth.ACT_READ, request_method='GET' )

	for name, view in { 'UserGeneratedData': '_UGDView',
						'RecursiveUserGeneratedData': '_RecursiveUGDView',
						'Stream': '_UGDStreamView',
						'RecursiveStream': '_RecursiveUGDStreamView',
						'UserGeneratedDataAndRecursiveStream': '_UGDAndRecursiveStreamView' }.items():
		for route in ('objects.generic.traversal', 'user.pages.odata.traversal'):
			pyramid_config.add_view(
				route_name=route, view='nti.appserver.dataserver_pyramid_views.' + view,
				context='nti.appserver.interfaces.IPageContainerResource',
				name=name, renderer='rest',
				permission=nauth.ACT_READ, request_method='GET' )

	pyramid_config.scan( 'nti.appserver.glossary_views' )


	# Modifying UGD
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest',
							 permission=nauth.ACT_DELETE, request_method='DELETE' )

	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EmptyContainerGetView',
							 renderer='rest', context='nti.appserver.interfaces.INewContainerResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.interfaces.IUserResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._method_not_allowed',
							 renderer='rest', context='nti.appserver.interfaces.IUserResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.dataserver.interfaces.IProviderOrganization',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._provider_redirect_classes',
							 renderer='rest', context='nti.dataserver.interfaces.IProviderOrganization',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.interfaces.IContainerResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.appserver.interfaces.IContainerResource',
							 permission=nauth.ACT_READ, request_method='GET' )

	# Modifying UGD beneath the Pages structure

	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPostView',
							 renderer='rest', context='nti.appserver.interfaces.IPagesResource',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest', context='nti.appserver.interfaces.IPagesResource',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest', context='zope.container.interfaces.IContained',
							 permission=nauth.ACT_DELETE, request_method='DELETE' )

	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='zope.container.interfaces.IContained',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )
	# And the user itself can be put to
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.appserver.interfaces.IUserResource',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )


	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDFieldPutView',
							 renderer='rest', context='nti.appserver.interfaces.IExternalFieldResource',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )


	# attached resources
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='zope.container.interfaces.IContained',
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
							 renderer='rest',context='zope.container.interfaces.IContained',
							 permission=nauth.ACT_READ, request_method='GET' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.dataserver.interfaces.ISimpleEnclosureContainer',
							 permission=nauth.ACT_READ, request_method='GET' )

	# ClassInfo conflicts with enclosures for PUT/POST somehow
	# TODO: This will all go away when we get to ++enclosures
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.dataserver.interfaces.IClassInfo',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='nti.dataserver.interfaces.IClassInfo',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.dataserver.interfaces.IClassInfo',
							 permission=nauth.ACT_READ, request_method='GET' )
	# TODO: Delete might be broken here as well

	# Restore DELETE for IFriendsList.
	# It is-a ISimpleEnclosureContainer, and that trumps before the request_method, sadly
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDDeleteView',
							 renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							 permission=nauth.ACT_DELETE, request_method='DELETE' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._UGDPutView',
							 renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							 permission=nauth.ACT_UPDATE, request_method='PUT' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._EnclosurePostView',
							 renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							 permission=nauth.ACT_CREATE, request_method='POST' )
	pyramid_config.add_view( route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							 renderer='rest',context='nti.dataserver.interfaces.IFriendsList',
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
	# TODO: Make these be utilities so they can be registered
	# in config and the expensive parts turned off in config dynamically.
	if create_ds:
		logger.info( 'Adding synchronous change listeners.' )
		server.add_change_listener( nti.dataserver.users.onChange )
		if indexmanager:
			server.add_change_listener( indexmanager.onChange )

		logger.info( 'Finished adding listeners' )


	main = _Main( pyramid_config, http_port=http_port )

	return (main,main) # bwc

import geventwebsocket.handler

class AppServer(gevent.pywsgi.WSGIServer):
	def __init__( self, *args, **kwargs ):
		kwargs['handler_class'] = geventwebsocket.handler.WebSocketHandler
		super(AppServer,self).__init__(*args, **kwargs)


# These two functions exist for the sake of the installed executables
# but they do nothing these days
def sharing_listener_main():
	pass

def index_listener_main():
	pass
