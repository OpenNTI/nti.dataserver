#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyramid WSGI application

.. $Id$
"""

import logging
logger = logging.getLogger(__name__)

import nti.dataserver as dataserver

import sys
if 'nti.monkey.patch_gevent_on_import' in sys.modules: # DON'T import this; it should already be imported if needed
	sys.modules['nti.monkey.patch_gevent_on_import'].check_threadlocal_status()

from nti.monkey import patch_webob_cookie_escaping_on_import
patch_webob_cookie_escaping_on_import.patch()

import os
import time
import warnings

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.configuration import xmlconfig

from zope.event import notify

from zope.processlifetime import ProcessStarting
from zope.processlifetime import DatabaseOpenedWithRoot
from zope.processlifetime import IDatabaseOpenedWithRoot

import pyramid.config
import pyramid.registry

from pyramid.threadlocal import get_current_registry

from paste.deploy.converters import asbool

from ZODB.interfaces import IDatabase

import nti.appserver

from nti.appserver import pyramid_auth
from nti.appserver import pyramid_predicates
from nti.appserver import pyramid_authorization
from nti.appserver import dataserver_socketio_views

from nti.appserver import interfaces as app_interfaces

from nti.appserver.traversal import ZopeResourceTreeTraverser

from nti.contentlibrary import interfaces as lib_interfaces

import nti.dataserver.users

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.interfaces import IDataserver

import nti.dictserver.storage

from nti.processlifetime import ApplicationTransactionOpenedEvent
from nti.processlifetime import IApplicationTransactionOpenedEvent

from nti.common import setupChameleonCache

## Make the zope interface extend the pyramid interface
## Although this seems backward, it isn't. The zope location
## proxy implements the zope interface, and we want
## that to match with pyramid
from pyramid.interfaces import ILocation
from zope.location.interfaces import ILocation as IZLocation
IZLocation.__bases__ = (ILocation,)

SOCKET_IO_PATH = 'socket.io'

def _create_xml_conf_machine( settings, features_file='' ):
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

	if os.path.isfile(features_file):
		xml_conf_machine = xmlconfig.file( features_file,
										   package=nti.appserver,
										   context=xml_conf_machine,
										   execute=True )

	# For testing, we need to be able to override some features
	# that we may have picked up from a file, specifically
	# to turn devmode back off to test production constraints
	if settings.get('force_devmode_off') and xml_conf_machine.hasFeature('devmode'):
		# Sadly, there is no public API to unprovide
		xml_conf_machine._features.remove('devmode')

	return xml_conf_machine

def _logon_account_views(pyramid_config):

	from nti.appserver.logon import ROUTE_OPENID_RESPONSE

	pyramid_config.add_route(name='logon.ping', pattern='/dataserver2/logon.ping')
	pyramid_config.add_route(name='logon.handshake', pattern='/dataserver2/logon.handshake')
	pyramid_config.add_route(name='logon.nti.password', pattern='/dataserver2/logon.nti.password')
	pyramid_config.add_route(name='logon.nti.impersonate', pattern='/dataserver2/logon.nti.impersonate',
							 factory='nti.appserver._dataserver_pyramid_traversal.dataserver2_root_resource_factory')
	pyramid_config.add_route(name='logon.google', pattern='/dataserver2/logon.google')
	pyramid_config.add_route(name='logon.google.oauth2', pattern='/dataserver2/logon.google.oauth2')

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

	# Not actually used anywhere; the logon.* routes are
	# pyramid_config.add_route( name='verify_openid', pattern='/dataserver2/openid.html' )
	# Note that the openid value MUST be POST'd to this view; an unmodified view goes into
	# an infinite loop if the openid value is part of a GET param
	# This value works for any google apps account: https://www.google.com/accounts/o8/id
	# pyramid_config.add_view( route_name='verify_openid', view='pyramid_openid.verify_openid' )
	# pyramid_config.add_view( name='verify_openid', route_name='verify_openid', view='pyramid_openid.verify_openid' )

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
	except StandardError:
		logger.warn("Failed to add dictionary server", exc_info=True)

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
	# the name rest is deprecated...
	pyramid_config.add_renderer(name='rest', factory='nti.app.renderers.renderers.DefaultRenderer')
	pyramid_config.add_renderer(name=None, factory='nti.app.renderers.renderers.DefaultRenderer')

	# Override the stock Chameleon template renderer to use z3c.pt for
	# better compatibility with the existing Zope stuff
	pyramid_config.add_renderer(name='.pt', factory='nti.app.pyramid_zope.z3c_zpt.renderer_factory')

	# Render PDF responses using a Zope Page Template that produces RML.
	# Note that the template lookup is only done on the last component of the filename
	# so we can't use ".rml.pt" or some-such
	pyramid_config.add_renderer(name='.rml', factory="nti.app.renderers.pdf.PDFRendererFactory")

def _notify_application_opened_event():
	import transaction
	conn = None
	try:
		with transaction.manager:
			# If we use db.transaction, we get a different transaction
			# manager than the default, which causes problems at commit time
			# if things tried to use transaction.get() to join it
			db = component.getUtility(IDatabase)
			conn = db.open()
			ds_site = conn.root()['nti.dataserver']
			with site(ds_site):
				notify(ApplicationTransactionOpenedEvent())
	finally:
		if conn is not None:
			try:
				conn.close()
			except StandardError:
				pass

@component.adapter(IApplicationTransactionOpenedEvent)
def _sync_global_library(_):
	library = component.getGlobalSiteManager().queryUtility(lib_interfaces.IContentPackageLibrary)

	if library is not None:
		# Ensure the library is enumerated at this time during startup
		# when we have loaded all the basic ZCML slugs but while
		# we are in control of the site.
		# NOTE: We are doing this in a transaction for the dataserver
		# to allow loading the packages to make persistent changes.
		library.syncContentPackages()

@component.adapter(IApplicationTransactionOpenedEvent)
def _sync_host_policies(_):
	# XXX: JAM: Note: this sync call will move around!
	from nti.site.hostpolicy import synchronize_host_policies
	synchronize_host_policies()

def _library_settings(pyramid_config, server):
	library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
	return library

def _ugd_odata_views(pyramid_config):

	_route_names = ('objects.generic.traversal',)

	def register_map(_m,
					 module='nti.appserver.ugd_query_views',
					 context='nti.appserver.interfaces.IPageContainerResource'):
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
	register_map(_m)

	# Relevant data we allow for both present and missing data
	_m = {'RelevantUserGeneratedData': '_RelevantUGDView',
		  'RelevantContainedUserGeneratedData': '_RelevantContainedUGDView'}
	register_map(_m, 'nti.appserver.relevant_ugd_views')
	register_map(_m, 'nti.appserver.relevant_ugd_views',
				 context='nti.appserver.interfaces.INewPageContainerResource')


	# As we do with recursive data
	_m = {'RecursiveUserGeneratedData': '_RecursiveUGDView',
		  'RecursiveStream': '_RecursiveUGDStreamView',
		  'UserGeneratedDataAndRecursiveStream': '_UGDAndRecursiveStreamView' }
	register_map(_m,
				 module='nti.appserver.ugd_query_views',
				 context='nti.appserver.interfaces.INewPageContainerResource')

	# The root is only for RecursiveStream, RecursiveUserGeneratedData
	# and "data generated by other people that I might be particularly interested in"
	_m = {'RecursiveStream': '_RecursiveUGDStreamView',
		  'RecursiveUserGeneratedData': '_RecursiveUGDView',
		  }
	register_map( _m,
				  module='nti.appserver.ugd_query_views',
				  context='nti.appserver.interfaces.IRootPageContainerResource' )

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_query_views.UGDFieldGetView',
							renderer='rest', context='nti.appserver.interfaces.IExternalFieldResource',
							permission=nauth.ACT_READ, request_method='GET')


def _modifying_ugd_views(pyramid_config):

	### XXX Why was this installed with no predicate?
	#pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDDeleteView',
	#						renderer='rest',
	#						permission=nauth.ACT_DELETE, request_method='DELETE')

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

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views.GenericGetView',
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
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views.GenericGetView',
							renderer='rest', context='nti.appserver.interfaces.IPagesResource',
							permission=nauth.ACT_READ, request_method='GET')

	# XXX: FIXME: This is wrong. These next two used to use:
	#	context='zope.container.interfaces.IContained',
	# But that's far too general, and as stock views they definitely
	# didn't work on plain implementations of that interface. In the best case
	# they blew up, in the worst case they silently did nothing.
	# So we're trying to be more specificy
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDDeleteView',
							renderer='rest',
							context='nti.dataserver.interfaces.IModeledContent',
							permission=nauth.ACT_DELETE, request_method='DELETE')


	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.ugd_edit_views.UGDPutView',
							renderer='rest',
							context='nti.dataserver.interfaces.IModeledContent',
							permission=nauth.ACT_UPDATE, request_method='PUT')

	# And the user itself can be put to
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.app.users.user_views.UserUpdateView',
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

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views.GenericGetView',
							renderer='rest', context='nti.dataserver.interfaces.IEnclosedContent',
							permission=nauth.ACT_READ, request_method='GET')

	# Restore GET for the things we can POST enclosures to
	# XXX: This is a pretty broad registration, we should almost certainly tone that down
	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views.GenericGetView',
							renderer='rest', context='zope.container.interfaces.IContained',
							permission=nauth.ACT_READ, request_method='GET')

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views.GenericGetView',
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

	pyramid_config.add_view(route_name='objects.generic.traversal', view='nti.appserver.dataserver_pyramid_views.GenericGetView',
							renderer='rest', context='nti.dataserver.interfaces.IFriendsList',
							permission=nauth.ACT_READ, request_method='GET')

def _create_server(create_ds, process_args=False):
	server = None

	if IDataserver.providedBy(create_ds):  # not isinstance( create_ds, bool ):
		server = create_ds
	elif not create_ds:
		raise ValueError("Must create a ds")
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
					   process_args=False,
					   create_ds=True,
					   pyramid_config=None,
					   **settings ):
	"""
	:keyword bool _return_xml_conf_machine: For testing only. If true,
	    instead of just the callable, we will return a tuple of the callable
	    and the XML configuration machine we used to load settings with. This
	    is useful for loading settings again in the future because it keeps track
	    of which files have already been loaded.

	:return: A WSGI callable.
	"""
	_return_xml_conf_machine = settings.pop('_return_xml_conf_machine', False)
	begin_time = time.time()

	# Configure subscribers, etc.
	__traceback_info__ = settings

	setHooks() # required for z3c.baseregistry

	# Let everything know about the settings
	component.getGlobalSiteManager().registerUtility(settings, app_interfaces.IApplicationSettings)

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

	xml_conf_machine = _create_xml_conf_machine( settings,
												 features_file=dataserver_file('etc', 'package-includes', '000-features.zcml') )

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

	if library_zcml and component.queryUtility(lib_interfaces.IContentPackageLibrary) is None:
		# If tests have already registered a library, use that instead
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
	component.getGlobalSiteManager().registerUtility(server, nti_interfaces.IDataserver)
	if server.chatserver:
		component.getGlobalSiteManager().registerUtility(server.chatserver)

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

	#content_type predicate for view_config.
	pyramid_config.add_view_predicate('content_type', pyramid_predicates.ContentTypePredicate)
	# Chameleon templating support; see also _renderer_settings
	pyramid_config.include( 'pyramid_chameleon' )
	# Configure Mako for plain text templates (Only! Use ZPT for XML/HTML)
	pyramid_config.registry.settings['mako.directories'] = 'nti.appserver:templates'
	pyramid_config.registry.settings['mako.module_directory'] = template_cache_dir
	# strict_undefined can be nice sometimes, but it makes writing certain
	# dynamic parts of templates extra hard since you can't even reference
	# a variable that isn't set, even to check to see if it's in the context or
	# locals
	#pyramid_config.registry.settings['mako.strict_undefined'] = True
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

	# First, before any "application" processing, hook in a place to run
	# greenlets with nothing below it on the stack
	pyramid_config.add_tween('nti.appserver.tweens.greenlet_runner_tween.greenlet_runner_tween_factory',
							 under=pyramid.tweens.EXCVIEW )


	# Next, connect to the database. We used to use pyramid_zodbconn,
	# which is not a tween just a set of request hooks (because the
	# pyramid command line doesn't run tweens). But we don't use that
	# command line, and i'm worried about the complexities of its
	# callback-based-closure. I prefer the simplicity of a try/finally block
	pyramid_config.add_tween('nti.appserver.tweens.zodb_connection_tween.zodb_connection_tween_factory',
							 under='nti.appserver.tweens.greenlet_runner_tween.greenlet_runner_tween_factory')

	# Then, ensure that each request is wrapped in default global transaction
	pyramid_config.add_tween( 'nti.appserver.tweens.transaction_tween.transaction_tween_factory',
							  under='nti.appserver.tweens.zodb_connection_tween.zodb_connection_tween_factory' )

	_configure_zodb_tween( DatabaseOpenedWithRoot( server.db ), pyramid_config.registry )

	# Add a tween that ensures we are within a SiteManager.
	pyramid_config.add_tween( 'nti.appserver.tweens.zope_site_tween.site_tween_factory',
							  under='nti.appserver.tweens.transaction_tween.transaction_tween_factory' )

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
	from pyramid.session import SignedCookieSessionFactory
	my_session_factory = SignedCookieSessionFactory(settings.get('session_cookie_secret',
																 settings.get('cookie_secret',
																			  '$Id$') ) + 'session',
													secure=asbool(settings.get('secure_cookies', True)),
													httponly=True)
	pyramid_config.set_session_factory( my_session_factory )

	pyramid_config.set_authorization_policy( pyramid_authorization.ZopeACLAuthorizationPolicy() )
	pyramid_auth.configure_authentication_policy(
		pyramid_config,
		secure_cookies=asbool( settings.get('secure_cookies', True) ),
		cookie_secret=settings.get('cookie_secret', '$Id$'))


	_logon_account_views(pyramid_config)
	_webapp_resource_views(pyramid_config, settings)

	_socketio_views(pyramid_config)
	_dictionary_views(pyramid_config, settings)

	_renderer_settings(pyramid_config)
	_library_settings(pyramid_config, server)

	# XXX: This is an arbitrary time to do this. Why are we doing it now?
	# (answer: the call to _library_settings used to do it)
	_notify_application_opened_event()

	_service_odata_views(pyramid_config)

	# Declarative configuration.
	# NOTE: More things are moving into this.
	# NOTE: This is hacked above, and also hacked below
	pyramid_config.load_zcml( 'nti.appserver:pyramid.zcml' ) # must use full spec, we may not have created the pyramid_config object so its working package may be unknown

	_ugd_odata_views(pyramid_config)

	# scan packages
	pyramid_config.scan('nti.appserver.ugd_query_views')
	pyramid_config.scan('nti.appserver.ugd_feed_views')
	pyramid_config.scan('nti.appserver.user_activity_views')

	_modifying_ugd_views(pyramid_config)

	_enclosure_views(pyramid_config)

	_patching_restore_views(pyramid_config)

	# Now load the registered pyramid slugs from buildout
	# XXX: HACK: The easiest way to do this, without
	# copying the pyramid_zcml code, is a second hack, overloading its
	# use of xmlconfig.file to actually take all the files in the directory,
	# ignoring the argument. A second option is a new ZCML directive,
	# if we could figure out how to get all the information to it
	# (maybe writing out a tempfile with arguments filled in?)
	# TODO: Or maybe using z3c.autoinclude from inside our own
	# pyramid.zcml would be best?
	class _pyramid_xmlconfig(object):
		def file( self, filename, package, context=None, execute=False ):
			# Ignore all that stuff except the context.
			load_dataserver_slugs( 'pyramid-includes', context )
	try:
		pyramid_zcml.xmlconfig = _pyramid_xmlconfig()
		pyramid_config.load_zcml( 'nti.appserver:pyramid.zcml' )
	finally:
		pyramid_zcml.xmlconfig = xmlconfig

	app = pyramid_config.make_wsgi_app()

	logger.info("Configured Dataserver in %.3fs", time.time() - begin_time)
	if _return_xml_conf_machine:
		return (app, xml_conf_machine)
	return app

@component.adapter(IDatabaseOpenedWithRoot)
def _configure_zodb_tween( database_event, registry=None ):
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
	registry.nti_zodb_root_db = database_event.database

####
# z3c.autoinclude plugin points:
# Although the first argument is specified as 'package', it actually
# takes any GlobalObject that has a __name__; the __name__ is what
# is used to look up plugins.
# We define a class and set of global objects to serve as proxies for
# the places that we do not actually have a package/configure.zcml to load.
####

class PluginPoint(object):
	__name__ = None

	def __init__(self, name):
		self.__name__ = name

# nti.app packages/plugins are meant to be part of the application
# always, on every site. they provide standard functionality.
PP_APP = PluginPoint('nti.app')

# nti.app.products packages/plugins are optional, installed
# and enabled on a site-by-site basis. they should be loaded second.
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

# nti.app.sits packages/plugins provide specific site policies
# and functionality. They should be loaded last.
PP_APP_SITES = PluginPoint('nti.app.sites')
