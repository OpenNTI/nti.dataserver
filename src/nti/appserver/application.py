#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyramid WSGI application

$Id$
"""

import logging
logger = logging.getLogger(__name__)

import nti.dataserver as dataserver

import sys
if 'nti.monkey.gevent_patch_on_import' in sys.modules: # DON'T import this; it should already be imported if needed
	sys.modules['nti.monkey.gevent_patch_on_import'].check_threadlocal_status()

import os
import random
import warnings
import time
import gevent

import nti.dictserver.storage

from nti.contentlibrary import interfaces as lib_interfaces

import nti.dataserver.users
from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserver
from nti.dataserver import interfaces as nti_interfaces

from zope import interface
from zope import component
from zope.event import notify
from zope import lifecycleevent
from zope.configuration import xmlconfig
from zope.component.hooks import setHooks, getSite, site
from zope.component.interfaces import IRegistrationEvent
from zope.processlifetime import ProcessStarting, DatabaseOpenedWithRoot, IDatabaseOpenedWithRoot

from nti.monkey import webob_cookie_escaping_patch_on_import
webob_cookie_escaping_patch_on_import.patch()

import pyramid.config
import pyramid.registry
from pyramid.threadlocal import get_current_registry

from paste.deploy.converters import asbool

import nti.appserver
from nti.appserver import pyramid_auth
from nti.appserver import pyramid_authorization
from nti.appserver import dataserver_socketio_views
from nti.appserver import interfaces as app_interfaces
from nti.appserver.contentlibrary import _question_map
from nti.appserver.contentlibrary import _videoindex_map
from nti.appserver.contentlibrary  import _related_content_map
from nti.appserver.traversal import ZopeResourceTreeTraverser

from nti.utils import setupChameleonCache

# Make the zope interface extend the pyramid interface
# Although this seems backward, it isn't. The zope location
# proxy implements the zope interface, and we want
# that to match with pyramid
from pyramid.interfaces import ILocation
from zope.location.interfaces import ILocation as IZLocation
IZLocation.__bases__ = (ILocation,)

SOCKET_IO_PATH = 'socket.io'

def _create_xml_conf_machine( settings ):
	xml_conf_machine = xmlconfig.ConfigurationMachine()
	xmlconfig.registerCommonDirectives( xml_conf_machine )

	zcml_features = settings.get( 'zcml_features', () )
	# Support reading from a string and direct code usage
	if isinstance( zcml_features, basestring ) and zcml_features:
		zcml_features = zcml_features.split()
	zcml_features = set(zcml_features)
	# BWC aliases
	for k in 'devmode', 'testmode':
		if asbool( settings.get( k ) ):
			zcml_features.add( k )

	if os.getenv('DATASERVER_DIR_IS_BUILDOUT'): # XXX Temp hack, mostly for tests
		zcml_features.add( 'in-buildout' )

	for feature in zcml_features:
		logger.info( "Enabling %s", feature )
		xml_conf_machine.provideFeature( feature )

	return xml_conf_machine

def _logon_account_views(pyramid_config):

	from nti.appserver.logon import ROUTE_OPENID_RESPONSE

	pyramid_config.add_route(name='logon.ping', pattern='/dataserver2/logon.ping')
	pyramid_config.add_route(name='logon.handshake', pattern='/dataserver2/logon.handshake')
	pyramid_config.add_route(name='logon.nti.password', pattern='/dataserver2/logon.nti.password')
	pyramid_config.add_route(name='logon.nti.impersonate', pattern='/dataserver2/logon.nti.impersonate',
							 factory='nti.appserver._dataserver_pyramid_traversal.dataserver2_root_resource_factory')
	pyramid_config.add_route(name='logon.google', pattern='/dataserver2/logon.google')

	pyramid_config.add_route(name=ROUTE_OPENID_RESPONSE, pattern='/dataserver2/' + ROUTE_OPENID_RESPONSE)
	pyramid_config.add_route(name='logon.openid', pattern='/dataserver2/logon.openid')
	pyramid_config.add_route(name='logon.logout', pattern='/dataserver2/logon.logout')
	pyramid_config.add_route(name='logon.facebook.oauth1', pattern='/dataserver2/logon.facebook1')
	pyramid_config.add_route(name='logon.facebook.oauth2', pattern='/dataserver2/logon.facebook2')

	if not os.getenv('DATASERVER_DIR_IS_BUILDOUT'): # XXX Temp hack
		warnings.warn("Installing route; move this to pyramid")
		pyramid_config.add_route(name='logon.ldap.ou', pattern='/dataserver2/logon.ldap.ou')

	pyramid_config.scan('nti.appserver.logon')

	# Deprecated logout alias
	pyramid_config.add_route(name='logout', pattern='/dataserver2/logout')
	pyramid_config.add_view(route_name='logout', view='nti.appserver.logon.logout')

	# 	# Not actually used anywhere; the logon.* routes are
	# 	pyramid_config.add_route( name='verify_openid', pattern='/dataserver2/openid.html' )
	# 	# Note that the openid value MUST be POST'd to this view; an unmodified view goes into
	# 	# an infinite loop if the openid value is part of a GET param
	# 	# This value works for any google apps account: https://www.google.com/accounts/o8/id
	# 	pyramid_config.add_view( route_name='verify_openid', view='pyramid_openid.verify_openid' )
	# 	pyramid_config.add_view( name='verify_openid', route_name='verify_openid', view='pyramid_openid.verify_openid' )

	pyramid_config.add_route(name="logon.forgot.username", pattern="/dataserver2/logon.forgot.username")
	pyramid_config.add_route(name="logon.forgot.passcode", pattern="/dataserver2/logon.forgot.passcode")
	pyramid_config.add_route(name="logon.reset.passcode", pattern="/dataserver2/logon.reset.passcode")

	pyramid_config.scan('nti.appserver.account_recovery_views')

def _webapp_resource_views(pyramid_config, settings):
	# Site-specific CSS packages
	web_root = settings.get('web_app_root', '/NextThoughtWebApp/')
	login_root = settings.get('login_app_root', '/login/')
	landing_root = settings.get('landing_root', '/landing/')

	pyramid_config.add_route(name="logon.logon_css", pattern=login_root + "resources/css/site.css")
	pyramid_config.add_route(name="logon.strings_js", pattern=login_root + "resources/strings/site.js")
	pyramid_config.add_route(name="webapp.site_css", pattern=web_root + "resources/css/site.css")
	pyramid_config.add_route(name="webapp.strings_js", pattern=web_root + "resources/strings/site.js")
	pyramid_config.add_route(name="landing.site_html", pattern=landing_root + "site.html")
	pyramid_config.scan('nti.appserver.policies.site_policy_views')

def _socketio_views(pyramid_config):
	pyramid_config.add_route(name=dataserver_socketio_views.RT_HANDSHAKE, pattern=dataserver_socketio_views.URL_HANDSHAKE)
	pyramid_config.add_route(name=dataserver_socketio_views.RT_CONNECT, pattern=dataserver_socketio_views.URL_CONNECT)
	pyramid_config.scan(dataserver_socketio_views)
	pyramid_config.add_static_view(SOCKET_IO_PATH + '/static/', 'nti.socketio:static/')

def _dictionary_views(pyramid_config, settings):
	if 'main_dictionary_path' not in settings:
		return

	try:
		storage = nti.dictserver.storage.UncleanSQLiteJsonDictionaryTermStorage(settings['main_dictionary_path'])
		dictionary = nti.dictserver.storage.JsonDictionaryTermDataStorage(storage)
		pyramid_config.registry.registerUtility(dictionary)
		logger.debug("Adding dictionary")
	except Exception:
		logger.exception("Failed to add dictionary server")

def _search_views(pyramid_config):
	# All the search views should accept an empty term (i.e., nothing after the trailing slash)
	# by NOT generating a 404 response but producing a 200 response with the same body
	# as if the term did not match anything. (This is what google does; the two alternatives
	# are to generate a 404--unfriendly and weird--or to treat it as a wildcard matching
	# everything--makes sense, but not scalable.)

	pyramid_config.add_route(name='search.user', pattern='/dataserver2/users/{user}/Search/RecursiveUserGeneratedData/{term:.*}',
							 traverse="/dataserver2/users/{user}")
	pyramid_config.add_view(route_name='search.user',
							view='nti.contentsearch.pyramid_views.UserSearch',
							renderer='rest',
							permission=nauth.ACT_SEARCH)

	# Unified search for content and user data. It should follow the same
	# security policies for user data search
	pyramid_config.add_route(name='search2.unified', pattern='/dataserver2/users/{user}/Search/UnifiedSearch/{ntiid}/{term:.*}',
							  traverse="/dataserver2/users/{user}")
	pyramid_config.add_view(route_name='search2.unified',
							view='nti.contentsearch.pyramid_views.Search',
							renderer='rest',
							permission=nauth.ACT_SEARCH)

def _service_odata_views(pyramid_config):
	# service
	pyramid_config.add_route(name='user.root.service', pattern='/dataserver2{_:/?}',
							 factory='nti.appserver._dataserver_pyramid_traversal.dataserver2_root_resource_factory')
	pyramid_config.add_view(route_name='user.root.service', view='nti.appserver.dataserver_pyramid_views._ServiceGetView',
							name='', renderer='rest',
							permission=nauth.ACT_READ, request_method='GET')

	# UGD in OData style
	# uses Pages(XXX)/.../
	# Our previous use of routes for this was inflexible and a poor
	# fit with traversal. We now make the ITraversable
	# handle this, preserving traversal flexibility.


def _renderer_settings(pyramid_config):
	pyramid_config.add_renderer(name='rest', factory='nti.appserver.pyramid_renderers.REST')

	# Override the stock Chameleon template renderer to use z3c.pt for better compatibility with the existing Zope stuff
	pyramid_config.add_renderer(name='.pt', factory='nti.app.pyramid_zope.z3c_zpt.renderer_factory')

def _library_settings(pyramid_config, server, library):
	if server:
		pyramid_config.registry.registerUtility(server, nti_interfaces.IDataserver)
		if server.chatserver:
			pyramid_config.registry.registerUtility(server.chatserver)

	if library is not None:
		component.getSiteManager().registerUtility(library, provided=lib_interfaces.IContentPackageLibrary)
	else:
		library = component.queryUtility(lib_interfaces.IContentPackageLibrary)

	if library is not None:
		# FIXME: This needs to move to the IRegistrationEvent listener, but
		# we need access to the pyramid config...
		# FIXME: This falls over in the presence of multiple libraries and/or
		# libraries configured only for specific sites. However, in those cases
		# we are probably in production and so not serving our own files anyway
		static_mapper = component.queryAdapter(library, app_interfaces.ILibraryStaticFileConfigurator)
		if static_mapper:
			static_mapper.add_static_views(pyramid_config)

	return library

def _external_view_settings(pyramid_config):
	for _, mapper in component.getUtilitiesFor(app_interfaces.IViewConfigurator):
		mapper.add_views(pyramid_config)

def _ugd_odata_views(pyramid_config):

	_route_names = ('objects.generic.traversal',)

	def register_map(_m, module, context='nti.appserver.interfaces.IPageContainerResource'):
		for name, view in _m.items():
			for route in _route_names:
				pyramid_config.add_view(route_name=route, view='%s.%s' % (module, view),
										context=context,
										name=name,
										renderer='rest',
										permission=nauth.ACT_READ,
										request_method='GET')

	_m = {'UserGeneratedData': '_UGDView',
		  'RecursiveUserGeneratedData': '_RecursiveUGDView',
		  'Stream': '_UGDStreamView',
		  'RecursiveStream': '_RecursiveUGDStreamView',
		  'UserGeneratedDataAndRecursiveStream': '_UGDAndRecursiveStreamView' }
	register_map(_m, 'nti.appserver.ugd_query_views')

	# Relevant data we allow for both present and missing data
	_m = {'RelevantUserGeneratedData': '_RelevantUGDView'}
	register_map(_m, 'nti.appserver.relevant_ugd_views')
	register_map(_m, 'nti.appserver.relevant_ugd_views',
				 context='nti.appserver.interfaces.INewPageContainerResource')


	# As we do with recursive data
	_m = {
		  'RecursiveUserGeneratedData': '_RecursiveUGDView',
		  'RecursiveStream': '_RecursiveUGDStreamView',
		  'UserGeneratedDataAndRecursiveStream': '_UGDAndRecursiveStreamView' }
	register_map(_m, 'nti.appserver.ugd_query_views',
				 context='nti.appserver.interfaces.INewPageContainerResource')


def _modifying_ugd_views(pyramid_config):

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDDeleteView',
							renderer='rest',
							permission=nauth.ACT_DELETE, request_method='DELETE')

	pyramid_config.add_view(route_name='objects.generic.traversal',
							view='nti.appserver.dataserver_pyramid_views._method_not_allowed',
							renderer='rest',
							context='nti.chatserver.interfaces.IMessageInfo',
							permission=nauth.ACT_DELETE, request_method='DELETE')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPostView',
							renderer='rest', context=nti_interfaces.IUser,
							permission=nauth.ACT_CREATE, request_method='POST')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPostView',
							renderer='rest', context='nti.appserver.interfaces.IContainerResource',
							permission=nauth.ACT_CREATE, request_method='POST')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							renderer='rest', context='nti.appserver.interfaces.IContainerResource',
							permission=nauth.ACT_READ, request_method='GET')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._method_not_allowed',
							renderer='rest', context='nti.appserver.interfaces.IObjectsContainerResource',
							permission=nauth.ACT_READ, request_method='GET')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPostView',
							renderer='rest', context='nti.appserver.interfaces.IObjectsContainerResource',
							permission=nauth.ACT_CREATE, request_method='POST')

	# Modifying UGD beneath the Pages structure

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPostView',
							renderer='rest', context='nti.appserver.interfaces.IPagesResource',
							permission=nauth.ACT_CREATE, request_method='POST')

	# XXX: FIXME: This is quite ugly. The GenericGetView relies on getting the (undocumented)
	# 'resource' from the PagesResource and turning it into a ICollection, which is what
	# we want to return (from the users workspace) for this URL. This relies on the default ICollection
	# adapter for the user.
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							renderer='rest', context='nti.appserver.interfaces.IPagesResource',
							permission=nauth.ACT_READ, request_method='GET')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDDeleteView',
							renderer='rest', context='zope.container.interfaces.IContained',
							permission=nauth.ACT_DELETE, request_method='DELETE')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPutView',
							renderer='rest', context='zope.container.interfaces.IContained',
							permission=nauth.ACT_UPDATE, request_method='PUT')

	# And the user itself can be put to
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPutView',
							renderer='rest', context=nti_interfaces.IUser,
							permission=nauth.ACT_UPDATE, request_method='PUT')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDFieldPutView',
							renderer='rest', context='nti.appserver.interfaces.IExternalFieldResource',
							permission=nauth.ACT_UPDATE, request_method='PUT')


def _enclosure_views(pyramid_config):

	# attached resources
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.enclosure_views.EnclosurePostView',
							renderer='rest', context='zope.container.interfaces.IContained',
							permission=nauth.ACT_CREATE, request_method='POST')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.enclosure_views.EnclosurePostView',
							renderer='rest', context='nti.dataserver.interfaces.ISimpleEnclosureContainer',
							permission=nauth.ACT_CREATE, request_method='POST')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.enclosure_views.EnclosurePutView',
							renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							permission=nauth.ACT_UPDATE, request_method='PUT')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.enclosure_views.EnclosureDeleteView',
							renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							permission=nauth.ACT_UPDATE, request_method='DELETE')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							permission=nauth.ACT_READ, request_method='GET')

	# Restore GET for the things we can POST enclosures to
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							renderer='rest', context='zope.container.interfaces.IContained',
							permission=nauth.ACT_READ, request_method='GET')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							renderer='rest', context='nti.dataserver.interfaces.ISimpleEnclosureContainer',
							permission=nauth.ACT_READ, request_method='GET')

def _patching_restore_views(pyramid_config):
	# Restore DELETE for IFriendsList.
	# It is-a ISimpleEnclosureContainer, and that trumps before the request_method, sadly
	# JAM: FIXME: This can probably go away with pyramid 1.5?
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDDeleteView',
							renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							permission=nauth.ACT_DELETE, request_method='DELETE')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPutView',
							renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							permission=nauth.ACT_UPDATE, request_method='PUT')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.enclosure_views.EnclosurePostView',
							renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							permission=nauth.ACT_CREATE, request_method='POST')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views._GenericGetView',
							renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							permission=nauth.ACT_READ, request_method='GET')

def _create_server(create_ds, process_args=False):
	server = None

	if IDataserver.providedBy(create_ds):  # not isinstance( create_ds, bool ):
		server = create_ds
	elif not create_ds:
		class MockServer(object):
			_parentDir = '.'
			_dataFileName = 'data.fs'
			db = None
			chatserver = None
		server = MockServer()
	else:
		ds_class = dataserver._Dataserver.Dataserver if not callable(create_ds) else create_ds
		if process_args:
			dataDir = None
			if '--dataDir' in sys.argv: dataDir = sys.argv[sys.argv.index('--dataDir') + 1]
			os.environ['DATASERVER_NO_REDIRECT'] = '1'
			server = ds_class(dataDir)
		else:
			server = ds_class()
	return server

def createApplication( http_port,
					   library=None,
					   process_args=False,
					   create_ds=True,
					   pyramid_config=None,
					   force_create_indexmanager=False, # For testing
					   **settings ):
	"""
	:return: A WSGI callable.
	"""
	begin_time = time.time()
	# Configure subscribers, etc.
	__traceback_info__ = settings

	setHooks() # required for z3c.baseregistry
	xml_conf_machine = _create_xml_conf_machine( settings )
	if 'pre_site_zcml' in settings:
		# One before we load the main config so it has a chance to exclude files
		logger.debug( "Loading pre-site settings from %s", settings['pre_site_zcml'] )
		xml_conf_machine = xmlconfig.file( settings['pre_site_zcml'],  package=nti.appserver, context=xml_conf_machine, execute=False )
	xml_conf_machine = xmlconfig.file( 'configure.zcml', package=nti.appserver, context=xml_conf_machine, execute=False )
	if 'site_zcml' in settings:
		logger.debug( "Loading site settings from %s", settings['site_zcml'] )
		xml_conf_machine = xmlconfig.file( settings['site_zcml'],  package=nti.appserver, context=xml_conf_machine, execute=False )
		# Preserve the conf machine so that when we load other files later any
		# exclude settings get processed

	if create_ds or force_create_indexmanager:
		# This may be excluded by a previous setting in site.zcml, and replaced with something else
		# If we are going to do it, it is important to do it as part of the same configuration transaction
		# as everything else, otherwise the proper listeners won't get called or won't
		# do the right thing (see e.g., _indexmanager_event_listeners)
		xml_conf_machine = xmlconfig.file( 'configure_indexmanager.zcml',  package=nti.appserver, context=xml_conf_machine, execute=False )

	DATASERVER_DIR = os.getenv('DATASERVER_DIR', '')
	dataserver_dir_exists = os.path.isdir( DATASERVER_DIR )
	if dataserver_dir_exists:
		DATASERVER_DIR = os.path.abspath( DATASERVER_DIR )
	def dataserver_file( *args ):
		return os.path.join( DATASERVER_DIR, *args )
	def is_dataserver_file( *args ):
		return dataserver_dir_exists and os.path.isfile( dataserver_file( *args ) )
	def is_dataserver_dir( *args ):
		return dataserver_dir_exists and os.path.isdir( dataserver_file( *args ) )

	def load_dataserver_slugs( include_dir_name, context ):
		if is_dataserver_dir( 'etc', include_dir_name ):
			# We need to include these files using the equivalent
			# of the include directive. If we load them directly using
			# xmlconfig.string, we lose context information about the include
			# paths, and then we can get duplicate registrations.
			# The files= parameter takes a shell-style glob,
			# finds the matches, and sorts them, and then includes
			# them.
			xmlconfig.include( context, files=dataserver_file('etc', include_dir_name, '*.zcml' ), package=nti.appserver )
			# This doesn't return a context, but that's ok,
			# it is modified in place.
		return context

	# Load the package include slugs created by buildout
	xml_conf_machine = load_dataserver_slugs( 'package-includes', xml_conf_machine )

	# Load a library, if needed. We take the first of:
	# settings['library_zcml']
	# $DATASERVER_DIR/etc/library.zcml
	# settings[__file__]/library.zcml
	# (This last is for existing environments and tests, as it lets us put a
	# file beside development.ini). In most environments, this can be handled
	# with site.zcml; NOTE: this could not be in pre_site_zcml, as we depend
	# on our configuration listeners being in place
	# TODO: Note that these should probably be configured by site (e.g, componont registery)
	# A global one is fine, but lower level sites need the ability to override it
	# easily.
	# This will come with the splitting of the policy files into their own
	# projects, together with buildout.
	library_zcml = None
	if 'library_zcml' in settings:
		library_zcml = settings['library_zcml']
	elif is_dataserver_file( 'etc', 'library.zcml'):
		library_zcml = dataserver_file( 'etc', 'library.zcml' )
	elif '__file__' in settings and os.path.isfile( os.path.join( os.path.dirname( settings['__file__'] ), 'library.zcml' ) ):
		library_zcml = os.path.join( os.path.dirname( settings['__file__'] ), 'library.zcml' )

	if library_zcml and library is None: # If tests pass in a library, use that instead
		library_zcml = os.path.normpath( os.path.expanduser( library_zcml ) )
		logger.debug( "Loading library settings from %s", library_zcml )
		xml_conf_machine = xmlconfig.file( library_zcml,  package=nti.appserver, context=xml_conf_machine, execute=False )

	xml_conf_machine.execute_actions()

	# Notify of startup. (Note that configuring the packages loads zope.component:configure.zcml
	# which in turn hooks up zope.component.event to zope.event for event dispatching)
	notify(ProcessStarting())

	logger.debug( 'Began starting dataserver' )
	template_cache_dir = setupChameleonCache(config=True) # must do this early

	server = _create_server(create_ds, process_args)

	logger.debug( 'Finished starting dataserver' )

	if pyramid_config is None:
		# We must use the global site manager as the registry, we cannot
		# let pyramid hook zca. This is because we install our local sites
		# (see site_policies) beneath the global registry and switch into
		# them, but the pyramid configuration still needs to be available.
		pyramid_config = pyramid.config.Configurator( registry=component.getGlobalSiteManager(),
													  debug_logger=logging.getLogger( 'pyramid' ),
													  package=nti.appserver,
													  settings=settings)
		# Note that because we're using the global registry, the Configurator doesn't
		# set it up. So all the arguments it would pass we must pass.
		# If we fail to do this, things like 'pyramid.includes' don't get processed
		pyramid_config.setup_registry(debug_logger=logging.getLogger( 'pyramid' ),
									  root_factory='._dataserver_pyramid_traversal.root_resource_factory',
									  settings=settings)

		# Note that the pyramid.registry.global_registry remains
		# the default registry, but it doesn't have the correct configuration.
		# Make it the GSM. Otherwise, outside of a request, e.g., when sending
		# chat events, the configuration is wrong.
		assert get_current_registry() is pyramid.registry.global_registry
		pyramid.registry.global_registry = component.getGlobalSiteManager()
		pyramid.threadlocal.global_registry = component.getGlobalSiteManager()
		assert get_current_registry() is component.getGlobalSiteManager()

	else:
		# This branch exists only for tests
		pyramid_config.set_root_factory( 'nti.appserver._dataserver_pyramid_traversal.root_resource_factory' )

	# Chameleon templating support; see also _renderer_settings
	pyramid_config.include( 'pyramid_chameleon' )
	# Configure Mako for plain text templates (Only! Use ZPT for XML/HTML)
	pyramid_config.registry.settings['mako.directories'] = 'nti.appserver:templates'
	pyramid_config.registry.settings['mako.module_directory'] = template_cache_dir
	pyramid_config.registry.settings['mako.strict_undefined'] = True
	# Disable all default filtering. Pyramid by default wants to apply HTML escaping,
	# which we clearly do not want as these are plain text templates (only!)
	# (NOTE: If you change this, you must manually remove any cached compiled templates)
	pyramid_config.registry.settings['mako.default_filters'] = None
	pyramid_config.include('pyramid_mako')
	pyramid_config.add_mako_renderer('.mako')
	pyramid_config.add_mako_renderer('.mak')
	# Our addons
	# include statsd client support around things we want to time.
	# This is only active if statsd_uri is defined in the config. Even if it is defined
	# and points to a non-existant server, UDP won't block
	pyramid_config.include( 'perfmetrics' )
	if pyramid_config.registry.settings.get( 'statsd_uri' ):
		# also set the default
		import perfmetrics
		perfmetrics.set_statsd_client( pyramid_config.registry.settings['statsd_uri'] )
	# First, ensure that each request is wrapped in default global transaction
	pyramid_config.add_tween( 'nti.appserver.tweens.transaction_tween.transaction_tween_factory', under=pyramid.tweens.EXCVIEW )

	# Arrange for a db connection to be opened with each request
	# if pyramid_zodbconn.get_connection() is called (until called, this does nothing)
	# TODO: We can probably replace this with something simpler, or else
	# better integrate this
	pyramid_config.include( 'pyramid_zodbconn' )
	_configure_pyramid_zodbconn( DatabaseOpenedWithRoot( server.db ), pyramid_config.registry )

	# Add a tween that ensures we are within a SiteManager.
	pyramid_config.add_tween( 'nti.appserver.tweens.zope_site_tween.site_tween_factory', under='nti.appserver.tweens.transaction_tween.transaction_tween_factory' )

	# And a tween that handles Zope security integration
	pyramid_config.add_tween( 'nti.appserver.tweens.zope_security_interaction_tween.security_interaction_tween_factory',
							  under='nti.appserver.tweens.zope_site_tween.site_tween_factory' )

	pyramid_config.include( 'pyramid_zcml' )
	import pyramid_zcml
	# XXX: HACK:  make it respect the features we choose to provide
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

	auth_policy, forbidden_view = pyramid_auth.create_authentication_policy(
		secure_cookies=asbool( settings.get('secure_cookies', False) ),
		cookie_secret=settings.get('cookie_secret', 'secret' ) )

	pyramid_config.set_authorization_policy( pyramid_authorization.ACLAuthorizationPolicy() )
	pyramid_config.set_authentication_policy( auth_policy )
	pyramid_config.add_forbidden_view( forbidden_view )

	_logon_account_views(pyramid_config)
	_webapp_resource_views(pyramid_config, settings)

	_socketio_views(pyramid_config)
	_dictionary_views(pyramid_config, settings)

	_renderer_settings(pyramid_config)
	_library_settings(pyramid_config, server, library)

	_search_views(pyramid_config)
	_service_odata_views(pyramid_config)

	# Declarative configuration.
	# NOTE: More things are moving into this.
	# NOTE: This is hacked above, and also hacked below
	pyramid_config.load_zcml( 'nti.appserver:pyramid.zcml' ) # must use full spec, we may not have created the pyramid_config object so its working package may be unknown

	_ugd_odata_views(pyramid_config)

	# scan packages
	pyramid_config.scan('nti.appserver.ugd_query_views')
	pyramid_config.scan('nti.appserver.ugd_feed_views')
	pyramid_config.scan('nti.appserver.glossary_views')
	pyramid_config.scan('nti.appserver.user_activity_views')

	_modifying_ugd_views(pyramid_config)

	_enclosure_views(pyramid_config)

	_patching_restore_views(pyramid_config)

	if not os.getenv('DATASERVER_DIR_IS_BUILDOUT'): # XXX Temp hack
		warnings.warn("External IViewConfigurators are deprecated and not used in buildouts; use pyramid.zcml")
		_external_view_settings(pyramid_config)

	# Now load the registered pyramid slugs from buildout
	# XXX: HACK: The easiest way to do this, without
	# copying the pyramid_zcml code, is a second hack, overloading its
	# use of xmlconfig.file to actually take all the files in the directory,
	# ignoring the argument. A second option is a new ZCML directive,
	# if we could figure out how to get all the information to it
	# (maybe writing out a tempfile with arguments filled in?)
	class _pyramid_xmlconfig(object):
		def file( self, filename, package, context=None, execute=False ):
			# Ignore all that stuff except the context.
			load_dataserver_slugs( 'pyramid-includes', context )
	try:
		pyramid_zcml.xmlconfig = _pyramid_xmlconfig()
		pyramid_config.load_zcml( 'nti.appserver:pyramid.zcml' )
	finally:
		pyramid_zcml.xmlconfig = xmlconfig

	# register change listeners
	# Now, fork off the change listeners
	# TODO: Make these be utilities so they can be registered
	# in config and the expensive parts turned off in config dynamically.
	if create_ds:
		_configure_async_changes( server )

	app = pyramid_config.make_wsgi_app()

	logger.debug( "Configured Dataserver in %.3fs", time.time() - begin_time )
	return app

def _configure_async_changes( ds, indexmanager=None ):

	import nti.contentsearch

	logger.info( 'Adding synchronous change listeners.' )
	ds.add_change_listener( nti.dataserver.users.onChange )
	indexmanager = indexmanager or component.queryUtility( nti.contentsearch.interfaces.IIndexManager )
	if indexmanager:
		ds.add_change_listener( indexmanager.onChange )

	logger.info( 'Finished adding listeners' )

@component.adapter(IDatabaseOpenedWithRoot)
def _configure_pyramid_zodbconn( database_event, registry=None ):
	# Notice that we're using the db from the DS directly, not requiring construction
	# of a new DB based on a URI; that is a second option if we don't want the
	# DS object 'owning' the DB. Also listens for database opened events; assumes
	# that there is only one ZODB open at a time

	# NOTE: It is not entirely clear how to get a connection to the dataserver if we're not
	# calling a method on the dataserver (and it doesn't have access to the request); however, it
	# is weird the way it is currently handled, with static fields of a context manager class.
	# I think the DS will want to be a transaction.interfaces.ISynchronizer and/or an IDataManager
	if registry is None:
		# event
		registry = component.getGlobalSiteManager()

	registry.zodb_database = database_event.database # 0.2
	registry._zodb_databases = { '': database_event.database } # 0.3, 0.4

@component.adapter(lib_interfaces.IFilesystemContentPackageLibrary)
@interface.implementer(app_interfaces.ILibraryStaticFileConfigurator)
class _FilesystemStaticFileConfigurator(object):

	def __init__(self, context):
		self.context = context

	def add_static_views(self, pyramid_config):
		# We'll volunteer to serve all the files in the root directory
		# Note that this is not dynamic (the library isn't either)
		# but in production we expect to have static files served by
		# nginx/apache; nor does it work with multiple trees of libraries
		# spread across sites (using the ContentUnitHrefMapper gets us closer)

		# Note: We are not configuring caching for these files, nor gzip. In production
		# usage, we MUST be behind a webserver that will deal with static
		# files correctly (nginx, apache) by applying ETags to allow caching and Content-Encoding
		# for speed.
		for package in self.context.contentPackages:
			# The href for the package will come out to be index.html;
			# we want to serve everything contained in that same directory
			prefix = os.path.dirname( lib_interfaces.IContentUnitHrefMapper( package ).href ) # Posix assumption
			path = package.dirname
			pyramid_config.add_static_view( prefix, path )

# These two functions exist for the sake of the installed executables
# but they do nothing these days
def sharing_listener_main():
	pass

def index_listener_main():
	pass

def _patch_pyramid_router_traceback():
	# An exact copy of pyramid.router:Router.__call__ as
	# of 1.5a2, with added traceback_info to help diagnose
	# weird "str is not callable"
	# This should be a very temporary patch, that's why
	# I'm not bothering to make it into an official monkey
	def __call__(self, environ, start_response):
		"""
		Accept ``environ`` and ``start_response``; create a
		:term:`request` and route the request to a :app:`Pyramid`
		view based on introspection of :term:`view configuration`
		within the application registry; call ``start_response`` and
		return an iterable.
		"""
		request = self.request_factory(environ)
		response = self.invoke_subrequest(request, use_tweens=True)
		__traceback_info__ = response, request, environ, start_response
		return response(request.environ, start_response)

	import pyramid.router
	pyramid.router.Router.__call__ = __call__

_patch_pyramid_router_traceback()
