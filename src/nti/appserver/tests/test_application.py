#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import greater_than_or_equal_to
from hamcrest import is_not
from hamcrest import contains, contains_inanyorder
from hamcrest import has_value
from hamcrest import same_instance
does_not = is_not
from nti.tests import is_empty

from nti.appserver.application import createApplication, _configure_async_changes
from nti.contentlibrary.filesystem import StaticFilesystemLibrary as Library
from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentsearch import interfaces as search_interfaces
from nti.externalization.externalization import to_json_representation
import nti.contentsearch
import nti.contentsearch.interfaces
import pyramid.config


from nti.appserver.tests import ConfiguringTestBase, SharedConfiguringTestBase
from webtest import TestApp as _TestApp
import webob.datetime_utils
import datetime
import time
import functools
import os
import os.path

import urllib
from nti.dataserver import users, classes, providers
from nti.ntiids import ntiids
from nti.dataserver.datastructures import ZContainedMixin
from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_external_object
from nti.contentrange import contentrange
from nti.dataserver import contenttypes
from nti.dataserver import datastructures
from nti.dataserver import links
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.tests import mock_dataserver

import anyjson as json
from urllib import quote as UQ
from persistent import Persistent
from zope import interface
from zope import component
from zope.deprecation import __show__

from zope.keyreference.interfaces import IKeyReference

@interface.implementer(IKeyReference) # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):

	def __str__( self ):
		if '_str' in self.__dict__:
			return self._str
		return "<%s %s>" % (self.__class__.__name__, self.to_container_key())

	def toExternalObject( self ):
		return str(self)
	def to_container_key(self):
		return to_external_ntiid_oid(self, default_oid=str(id(self)))


class PersistentContainedExternal(ContainedExternal,Persistent):
	pass

import contextlib
from ZODB.interfaces import IConnection
from zope.component.hooks import site as using_site
import transaction

@contextlib.contextmanager
def _trivial_db_transaction_cm():
	# TODO: This needs all the retry logic, etc, that we
	# get in the main app through pyramid_tm

	lsm = component.getSiteManager()
	conn = IConnection( lsm, None )
	if conn:
		yield conn
		return

	ds = component.getUtility( nti_interfaces.IDataserver )
	transaction.begin()
	conn = ds.db.open()
	# If we don't sync, then we can get stale objects that
	# think they belong to a closed connection
	# TODO: Are we doing something in the wrong order? Connection
	# is an ISynchronizer and registers itself with the transaction manager,
	# so we shouldn't have to do this manually
	# ... I think the problem was a bad site. I think this can go away.
	conn.sync()
	sitemanc = conn.root()['nti.dataserver']


	with using_site( sitemanc ):
		assert component.getSiteManager() == sitemanc.getSiteManager()
		assert component.getUtility( nti_interfaces.IDataserver )
		try:
			yield conn
			transaction.commit()
		except:
			transaction.abort()
			raise
		finally:
			conn.close()

from nti.appserver.cors import cors_filter_factory as CORSInjector, cors_option_filter_factory as CORSOptionHandler
from paste.exceptions.errormiddleware import ErrorMiddleware

class ZODBGCMiddleware(object):

	def __init__( self, app ):
		self.app = app

	def __call__( self, *args, **kwargs ):
		result = self.app( *args, **kwargs )
		mock_dataserver.reset_db_caches( )
		return result


class _UnicodeTestApp(_TestApp):
	"To make using unicode literals easier"

	def _make_( name ):
		def f( self, path, *args, **kwargs ):
			__traceback_info__ = path, args, kwargs
			return getattr( super(_UnicodeTestApp,self), name )( str(path), *args, **kwargs )

		f.__name__ = name
		return f

	get = _make_('get')
	put = _make_('put')
	post = _make_('post')
	put_json = _make_('put_json')
	post_json = _make_('post_json')
	delete = _make_( 'delete' )

	del _make_

_TestApp = _UnicodeTestApp

def TestApp(app, **kwargs):
	"""Sets up the pipeline just like in real life.

	:return: A WebTest testapp.
	"""

	return _TestApp( CORSInjector( CORSOptionHandler( ErrorMiddleware( ZODBGCMiddleware( app ), debug=True ) ) ),
					 **kwargs )
TestApp.__test__ = False # make nose not call this

class _AppTestBaseMixin(object):

	default_user_extra_interfaces = ()
	extra_environ_default_user = b'sjohnson@nextthought.COM'
	default_origin = b'http://localhost'

	default_community = None

	def _make_extra_environ(self, user=None, update_request=False, **kwargs):
		"""
		The default username is a case-modified version of the default user in :meth:`_create_user`,
		to test case-insensitive ACLs and login.
		"""
		if user is None:
			user = self.extra_environ_default_user

		if user is self.extra_environ_default_user and 'username' in kwargs:
			user = str(kwargs.pop( 'username' ) )

		# Simulate what some browsers or command line clients do by encoding the '@'
		user = user.replace( '@', "%40" )
		result = {
			b'HTTP_AUTHORIZATION': b'Basic ' + (user + ':temp001').encode('base64'),
			b'HTTP_ORIGIN': self.default_origin, # To trigger CORS
			b'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6',
			b'paste.throw_errors': True, # Cause paste to throw everything in case it gets in the pipeline
			}
		for k, v in kwargs.items():
			k = str(k)
			k.replace( '_', '-' )
			result[k] = v

		if update_request:
			self.request.environ.update( result )

		return result

	def _create_user(self, username=None, password='temp001', **kwargs):
		if username is None:
			username = self.extra_environ_default_user.lower()
			ifaces = self.default_user_extra_interfaces
		else:
			ifaces = kwargs.pop( 'extra_interfaces', () )

		user = users.User.create_user( self.ds, username=username, password=password, **kwargs)
		interface.alsoProvides( user, ifaces )

		if self.default_community:
			comm = users.Community.get_community( self.default_community, self.ds )
			if not comm:
				comm = users.Community.create_community( self.ds, username=self.default_community )
			user.join_community( comm )

		return user

	def _fetch_user_url( self, path, testapp=None, username=None, **kwargs ):
		if testapp is None:
			testapp = self.testapp
		if username is None:
			username = self.extra_environ_default_user

		return testapp.get( '/dataserver2/users/' + username + path, **kwargs )


	def resolve_user_response( self, testapp=None, username=None, **kwargs ):
		if testapp is None:
			testapp = self.testapp
		if username is None:
			username = self.extra_environ_default_user

		return testapp.get( UQ('/dataserver2/ResolveUser/' + username), **kwargs )


	def resolve_user( self, *args, **kwargs ):
		return self.resolve_user_response( *args, **kwargs ).json_body['Items'][0]

	def fetch_service_doc( self, testapp=None ):
		if testapp is None:
			testapp = self.testapp
		return testapp.get( '/dataserver2' )

	def fetch_user_activity( self, testapp=None, username=None ):
		"Using the given or default app, fetch the activity for the given or default user"
		return self._fetch_user_url( '/Activity', testapp=testapp, username=username )

	def fetch_user_root_rugd( self, testapp=None, username=None, **kwargs ):
		"Using the given or default app, fetch the RecursiveUserGeneratedData for the given or default user"
		return self._fetch_user_url( '/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData', testapp=testapp, username=username, **kwargs )

	def fetch_user_root_rstream( self, testapp=None, username=None, **kwargs ):
		"Using the given or default app, fetch the RecursiveStream for the given or default user"
		return self._fetch_user_url( '/Pages(' + ntiids.ROOT + ')/RecursiveStream', testapp=testapp, username=username, **kwargs )

	def search_user_rugd( self, term, testapp=None, username=None, **kwargs ):
		"""Search the user for the given term and return the results"""
		return self._fetch_user_url( '/Search/RecursiveUserGeneratedData/' + term, testapp=testapp, username=username, **kwargs )

	def fetch_by_ntiid( self, ntiid, testapp=None, **kwargs ):
		"Using the given or default app, fetch the object with the given ntiid"
		if testapp is None:
			testapp = self.testapp

		return testapp.get( '/dataserver2/NTIIDs/' + ntiid, **kwargs )

from zope.component import eventtesting
class SharedApplicationTestBase(_AppTestBaseMixin,SharedConfiguringTestBase):
	features = ()
	set_up_packages = () # None, because configuring the app will do this
	APP_IN_DEVMODE = True
	configure_events = False # We have no packages, but we will set up the listeners ourself when configuring the app

	@classmethod
	def _setup_library(cls, *args, **kwargs):
		return Library()

	@classmethod
	def setUpClass(cls):
		__show__.off()
		#self.ds = mock_dataserver.MockDataserver()
		super(SharedApplicationTestBase,cls).setUpClass()
		cls.app, cls.main = createApplication( 8080, cls._setup_library(), create_ds=False, force_create_indexmanager=True,
											   pyramid_config=cls.config, devmode=cls.APP_IN_DEVMODE, testmode=True, zcml_features=cls.features )

		root = '/Library/WebServer/Documents/'
		# We'll volunteer to serve all the files in the root directory
		# This SHOULD include 'prealgebra' and 'mathcounts'
		serveFiles = [ ('/' + s, os.path.join( root, s) )
					   for s in os.listdir( root )
					   if os.path.isdir( os.path.join( root, s ) )]
		cls.main.setServeFiles( serveFiles )
		component.provideHandler( eventtesting.events.append, (None,) )

	def setUp(self):
		super(SharedApplicationTestBase,self).setUp()

		test_func = getattr( self, self._testMethodName )
		#ds_factory = getattr( test_func, 'mock_ds_factory', mock_dataserver.MockDataserver )
		#self.ds = ds_factory()
		#component.provideUtility( self.ds, nti_interfaces.IDataserver )

		# If we try to externalize things outside of an active request, but
		# the get_current_request method returns the mock request we just set up,
		# then if the environ doesn't have these things in it we can get an AssertionError
		# from paste.httpheaders n behalf of repoze.who's request classifier
		self.beginRequest()
		self.request.environ[b'HTTP_USER_AGENT'] = b'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6'
		self.request.environ[b'wsgi.version'] = '1.0'

		self.users = {}
		self.testapp = None

	def tearDown(self):
		self.users = {}
		self.testapp = None
		super(SharedApplicationTestBase,self).tearDown()

	@classmethod
	def tearDownClass(cls):
		__show__.on()
		super(SharedApplicationTestBase,cls).tearDownClass()

def WithSharedApplicationMockDS( *args, **kwargs ):
	"""
	Decorator for a test function using the shared application.
	Unknown keyword arguments are passed to :func:`.WithMockDS`.

	:keyword users: Either `True`, or a sequence of strings naming users. If True,
		 then the standard user is created. If a sequence, then the standard user,
		 followed by each named user is created.
	:keyword bool default_authenticate: Only used if ``users`` was a sequence
		(and so we have created at least two users). If set to `True` (NOT the default),
		then ``self.testapp`` will be authenticated by the standard user.
	:keyword bool testapp: If True (NOT the default) then ``self.testapp`` will
		be created.
	:keyword bool handle_changes: If `True` (NOT the default), the application will
		have the usual change managers set up (users.onChange, etc).

	"""

	users_to_create = kwargs.pop( 'users', None )
	default_authenticate = kwargs.pop( 'default_authenticate', None )
	testapp = kwargs.pop( 'testapp', None )
	handle_changes = kwargs.pop( 'handle_changes', False )
	user_hook = kwargs.pop( 'user_hook', None )

	if testapp:
		def _make_app(self):
			if users_to_create is True or (users_to_create and default_authenticate):
				self.testapp = TestApp( self.app, extra_environ=self._make_extra_environ() )
			else:
				self.testapp = TestApp( self.app )

			if handle_changes:
				ds = self.ds
				ix = component.queryUtility( search_interfaces.IIndexManager )
				_configure_async_changes( ds, ix )
	else:
		def _make_app( self ):
			pass

	if users_to_create:
		def _do_create(self):
			with mock_dataserver.mock_db_trans( self.ds ):
				base_user = self._create_user()
				self.users = { base_user.username: base_user }
				if user_hook:
					user_hook( base_user )
				if users_to_create and users_to_create is not True:
					for username in users_to_create:
						self.users[username] = self._create_user( username )
	else:
		def _do_create(self):
			pass

	if handle_changes:
		kwargs['with_changes'] = True # make sure the DS gets it

	if len(args) == 1 and not kwargs:
		# being used as a decorator
		func = args[0]

		@functools.wraps(func)
		@mock_dataserver.WithMockDS
		def f(self):
			self.config.registry._zodb_databases = { '': self.ds.db } # 0.3
			_do_create( self )
			_make_app( self )
			func(self)
		return f

	# Being used as a decorator factory
	def factory(func):
		@functools.wraps(func)
		@mock_dataserver.WithMockDS(**kwargs)
		def f(self):
			self.config.registry._zodb_databases = { '': self.ds.db } # 0.3
			_do_create( self )
			_make_app( self )
			func(self)
		return f
	return factory

def WithSharedApplicationMockDSHandleChanges( *args, **kwargs ):
	call_factory = False
	if len(args) == 1 and not kwargs:
		# Being used as a plain decorator. But we add kwargs that make
		# it look like we're being used as a factory
		call_factory = True

	kwargs['handle_changes'] = True
	if 'testapp' not in kwargs:
		kwargs['testapp'] = True
	result = WithSharedApplicationMockDS( *args, **kwargs )
	if call_factory:
		result = result(args[0])
	return result

def WithSharedApplicationMockDSWithChanges(func):
	@functools.wraps(func)
	@mock_dataserver.WithMockDS(with_changes=True)
	def f(self):
		self.config.registry._zodb_databases = { '': self.ds.db } # 0.3
		func(self)
	return f


class ApplicationTestBase(_AppTestBaseMixin, ConfiguringTestBase):

	set_up_packages = () # None, because configuring the app will do this
	APP_IN_DEVMODE = True
	def _setup_library(self, *args, **kwargs):
		return Library()

	def setUp(self):
		__show__.off()
		super(ApplicationTestBase,self).setUp(pyramid_request=False)
		#self.ds = mock_dataserver.MockDataserver()
		test_func = getattr( self, self._testMethodName )
		ds_factory = getattr( test_func, 'mock_ds_factory', mock_dataserver.MockDataserver )

		self.app, self.main = createApplication( 8080, self._setup_library(), create_ds=ds_factory, pyramid_config=self.config, devmode=self.APP_IN_DEVMODE, testmode=True )
		self.ds = component.getUtility( nti_interfaces.IDataserver )
		root = '/Library/WebServer/Documents/'
		# We'll volunteer to serve all the files in the root directory
		# This SHOULD include 'prealgebra' and 'mathcounts'
		serveFiles = [ ('/' + s, os.path.join( root, s) )
					   for s in os.listdir( root )
					   if os.path.isdir( os.path.join( root, s ) )]
		self.main.setServeFiles( serveFiles )

		# If we try to externalize things outside of an active request, but
		# the get_current_request method returns the mock request we just set up,
		# then if the environ doesn't have these things in it we can get an AssertionError
		# from paste.httpheaders n behalf of repoze.who's request classifier
		self.beginRequest()
		self.request.environ[b'HTTP_USER_AGENT'] = b'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.6 (KHTML, like Gecko) Chrome/23.0.1239.0 Safari/537.6'
		self.request.environ[b'wsgi.version'] = '1.0'


	def tearDown(self):
		__show__.on()
		super(ApplicationTestBase,self).tearDown()



class TestApplication(SharedApplicationTestBase):

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_unauthenticated_userid(self):
		from pyramid.interfaces import IAuthenticationPolicy
		auth_policy = component.getUtility(IAuthenticationPolicy)
		assert_that( auth_policy.unauthenticated_userid(self.request), is_( none() ) )
		self._make_extra_environ( update_request=True )
		with mock_dataserver.mock_db_trans(self.ds):
			assert_that( auth_policy.unauthenticated_userid(self.request), is_( self.extra_environ_default_user.lower() ) )

	def test_locale_negotionion( self ):
		from zope.i18n.interfaces import IUserPreferredLanguages
		self.request.environ['HTTP_ACCEPT_LANGUAGE'] = 'en'
		langs = IUserPreferredLanguages( self.request )
		assert_that( langs.getPreferredLanguages(), is_( ['en'] ) )

		from zope.i18n.interfaces import IUserPreferredCharsets
		chars = IUserPreferredCharsets( self.request )
		assert_that( chars.getPreferredCharsets(), is_( ['utf-8'] ) ) # default

		self.request.environ['HTTP_ACCEPT_CHARSET'] = 'iso-8859-1'
		assert_that( chars.getPreferredCharsets(), is_( ['iso-8859-1'] ) )

	@WithSharedApplicationMockDS
	def test_chameleon_caching_config(self):
		assert_that( self.app, is_( not_none() ) )
		# chameleon is imported by pyramid.
		# it is also imported by us. But depending on the order
		# of imports, chameleon may have gotten initialized too soon
		# and not be using module loaders. see nti.util
		import chameleon.config
		import chameleon.template
		import chameleon.loader
		assert_that( chameleon.config.CACHE_DIRECTORY, is_( not_none() ) )
		assert_that( chameleon.template.CACHE_DIRECTORY, is_( same_instance( chameleon.config.CACHE_DIRECTORY ) ) )
		assert_that( chameleon.template.BaseTemplate, has_property( 'loader', is_(chameleon.loader.ModuleLoader) ) )

	@WithSharedApplicationMockDS
	def test_logon_css_site_policy(self):
		testapp = TestApp(self.app)
		# No site, empty file
		res = testapp.get( '/login/resources/css/site.css' )
		assert_that( res, has_property( 'content_type', 'text/css' ) )

		# Configured site, redirect
		res = testapp.get( '/login/resources/css/site.css', extra_environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'}, status=303 )
		assert_that( res.headers, has_entry( 'Location', ends_with( '/login/resources/css/mathcounts.nextthought.com/site.css' ) ) )

	@WithSharedApplicationMockDS
	def test_external_coppa_capabilities_mathcounts(self):
		# See also test_workspaces
		testapp = TestApp(self.app)
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )


		res = testapp.get( '/dataserver2',
						   extra_environ=self._make_extra_environ( HTTP_ORIGIN=b'http://mathcounts.nextthought.com' ),
						   status=200 )
		assert_that( res.json_body['CapabilityList'], is_empty() )


	@WithSharedApplicationMockDS
	def test_options_request( self ):
		testapp = TestApp( self.app )
		res = testapp.options( '/dataserver2/logon.ping', extra_environ=self._make_extra_environ() )
		assert_that( res.headers, has_key( 'Access-Control-Allow-Methods' ) )

	@WithSharedApplicationMockDS
	def test_logon_ping(self):
		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/logon.ping' )

		assert_that( res.json_body, has_key( 'Links' ) )

		link_rels = [l['rel'] for l in res.json_body['Links']]
		assert_that( link_rels, has_item( 'account.create' ) )
		assert_that( link_rels, has_item( 'account.preflight.create' ) )

	@WithSharedApplicationMockDS
	def test_logon_ping_demo_site_policy(self):
		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/logon.ping', extra_environ={b'HTTP_ORIGIN': b'http://demo.nextthought.com'} )

		assert_that( res.json_body, has_key( 'Links' ) )

		link_rels = [l['rel'] for l in res.json_body['Links']]
		assert_that( link_rels, does_not( has_item( 'account.create' ) ) )
		assert_that( link_rels, does_not( has_item( 'account.preflight.create' ) ) )

	@WithSharedApplicationMockDS
	def test_library_main(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Library/Main', extra_environ=self._make_extra_environ() )
		assert_that( res.cache_control, has_property( 'max_age', 120 ) )

	@WithSharedApplicationMockDS
	def test_resolve_root_ntiid(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/NTIIDs/' + ntiids.ROOT,
						   headers={"Accept": 'application/json' },
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )


	@WithSharedApplicationMockDS
	def test_path_with_parens(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user( )
			container_id = contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + container_id + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )

	@WithSharedApplicationMockDS
	def test_pages_with_only_shared_not_404(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = PersistentContainedExternal()
			contained.lastModified = 0
			user = self._create_user()
			container_id = contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )

			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )
			contained_str = str(contained)
			contained._str = contained_str

			user2 = self._create_user( username='foo@bar' )
			user2._addSharedObject( contained )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/foo@bar/Pages(' + container_id + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))

		assert_that( res.body, contains_string( contained_str ) )

		# It should also show up in the RecursiveStream
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/vnd.nextthought+json'))

		# And the feed
		path = path + '/feed.atom'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/atom+xml'))

	@WithSharedApplicationMockDS
	def test_deprecated_path_with_slash(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user()
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/' + contained.containerId + '/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )


	@WithSharedApplicationMockDSWithChanges
	def test_post_pages_collection(self):
		self.ds.add_change_listener( users.onChange )

		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()
			_user2 = self._create_user( username='foo@bar' )

		testapp = TestApp( self.app )
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_HTML, specific='1234' )
		data = json.serialize( { 'Class': 'Highlight',
								 'MimeType': 'application/vnd.nextthought.highlight',
								 'ContainerId': containerId,
								 'sharedWith': ['foo@bar'],
								 'selectedText': 'This is the selected text',
								 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		href = res.json_body['href']
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )

		# The object can be found in the UGD sub-collection
		for username in ('sjohnson@nextthought.com', 'foo@bar'):
			path = '/dataserver2/users/'+username+'/Pages/' + containerId + '/UserGeneratedData'
			res = testapp.get( path, extra_environ=self._make_extra_environ(user=username))
			assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )

		# And the feed for the other user (not ourself)
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.atom'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/atom+xml'))
		assert_that( res.body, contains_string( "This is the selected text" ) )


		# The pages collection should have complete URLs
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages'
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = res.json_body
		links = body['Collection']['Links']
		assert_that( links, has_item( has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Search/RecursiveUserGeneratedData' ) ) )
		assert_that( body, has_entry( 'Items', has_length( 2 ) ) )
		for item in body['Items']:
			item_id = item['ID']
			links = item['Links']
			assert_that( links, has_item( has_entry( 'href',
														 urllib.quote( '/dataserver2/users/sjohnson@nextthought.com/Pages(%s)/RecursiveStream' % item_id ) ) ) )

		# I can now delete that item
		testapp.delete( str(href), extra_environ=self._make_extra_environ())


	@WithSharedApplicationMockDS
	def test_get_highlight_by_oid_has_links(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		data = json.serialize( { 'Class': 'Highlight', 'MimeType': 'application/vnd.nextthought.highlight',
								 'ContainerId': containerId,
								 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )


		path = res.headers['Location']
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_(200) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links',
									  has_item( all_of(
										  has_entry( 'href', contains_string( '/dataserver2/users/sjohnson%40nextthought.com/Objects/tag' ) ),
										  has_entry( 'rel', 'edit' ) ) ) ))

	@WithSharedApplicationMockDS
	def test_post_two_friendslist_same_name(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'FriendsList',  'MimeType': 'application/vnd.nextthought.friendslist',
								 'ContainerId': 'FriendsLists',
								 'ID': "Foo@bar" } )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		testapp.post( path, data, extra_environ=self._make_extra_environ() )
		# Generates a conflict the next time
		testapp.post( path, data, extra_environ=self._make_extra_environ(), status=409 )

	@WithSharedApplicationMockDS
	def test_friends_list_unmodified(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( none() ) )

	@WithSharedApplicationMockDS
	def test_post_device(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'Device', 'MimeType': 'application/vnd.nextthought.device',
								 'ContainerId': 'Devices',
								 'ID': "deadbeef" } )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.device' ) )
		# Generates a conflict the next time
		testapp.post( path, data, extra_environ=self._make_extra_environ(), status=409 )

	@WithSharedApplicationMockDS
	def test_put_device(self):
		"Putting a non-existant device is not possible"
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'Device',
								 'ContainerId': 'Devices',
								 'ID': "deadbeef" } )
		path = '/dataserver2/users/sjohnson@nextthought.com/Devices/deadbeef'
		testapp.put( path, data, extra_environ=self._make_extra_environ(), status=404 )
		# But we can post it
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
		# And then put
		__traceback_info__ = path
		testapp.put( path, data, extra_environ=self._make_extra_environ(), status=200 )

	@WithSharedApplicationMockDS
	def test_post_restricted_types(self):
		data = {u'Class': 'Canvas',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.canvas',
				'shapeList': [{u'Class': 'CanvasUrlShape',
							   u'MimeType': u'application/vnd.nextthought.canvasurlshape',
							   u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()


		json_data = json.serialize( data )

		testapp = TestApp( self.app )

		# Without restrictions, we can post it
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data, extra_environ=self._make_extra_environ() )

		# If we become restricted, we cannot post it
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( 'sjohnson@nextthought.com' )
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data,
					  extra_environ=self._make_extra_environ(),
					  status=403 ) # Forbidden!

	@WithSharedApplicationMockDS
	def test_post_canvas_image_roundtrip_download_views(self):
		" Images posted as data urls come back as real links which can be fetched "
		data = {u'Class': 'Canvas',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.canvas',
				'shapeList': [{u'Class': 'CanvasUrlShape',
							   u'MimeType': u'application/vnd.nextthought.canvasurlshape',
							   u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()


		json_data = json.serialize( data )

		testapp = TestApp( self.app )

		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data, extra_environ=self._make_extra_environ() )

		canvas = res.json_body
		assert_that( canvas, has_entry( 'shapeList', has_length( 1 ) ) )
		assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'Class', 'CanvasUrlShape' ) ) ) )
		assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'url', contains_string( '/dataserver2/' ) ) ) ) )
		canvas_res = res

		res = testapp.get( canvas['shapeList'][0]['url'], extra_environ=self._make_extra_environ() )
		# The content type is preserved
		assert_that( res, has_property( 'content_type', 'image/gif' ) )
		# The modified date is the same as the canvas containing it
		assert_that( res, has_property( 'last_modified', not_none() ) )
		assert_that( res, has_property( 'last_modified', canvas_res.last_modified ) )

	@WithSharedApplicationMockDS
	def test_post_canvas_in_note_image_roundtrip_download_views(self):
		" Images posted as data urls come back as real links which can be fetched "
		canvas_data = {u'Class': 'Canvas',
					   'ContainerId': 'tag:foo:bar',
					   u'MimeType': u'application/vnd.nextthought.canvas',
					   'shapeList': [{u'Class': 'CanvasUrlShape',
									  u'MimeType': u'application/vnd.nextthought.canvasurlshape',
									  u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}
		data = {'Class': 'Note',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.note',
				'applicableRange': {'Class': 'ContentRangeDescription'},
				'body': [canvas_data]}

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()


		json_data = json.serialize( data )

		testapp = TestApp( self.app )

		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data, extra_environ=self._make_extra_environ() )

		def _check_canvas( res ):
			canvas = res.json_body['body'][0]
			assert_that( canvas, has_entry( 'shapeList', has_length( 1 ) ) )
			assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'Class', 'CanvasUrlShape' ) ) ) )
			assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'url', contains_string( '/dataserver2/' ) ) ) ) )


			res = testapp.get( canvas['shapeList'][0]['url'], extra_environ=self._make_extra_environ() )
			# The content type is preserved
			assert_that( res, has_property( 'content_type', 'image/gif' ) )
			# The modified date is the same as the canvas containing it
			assert_that( res, has_property( 'last_modified', not_none() ) )
		#	assert_that( res, has_property( 'last_modified', canvas_res.last_modified ) )

		_check_canvas( res )

		# If we "edit" the data, then nothing breaks
		edit_link = None
		for l in res.json_body['Links']:
			if l['rel'] == 'edit':
				edit_link = l['href']
				break
		res = testapp.put( edit_link.encode('ascii'), res.body, extra_environ=self._make_extra_environ() )
		_check_canvas( res )

		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( user.username )
			note = user.getContainedObject( res.json_body['ContainerId'], res.json_body['ID'] )
			canvas = note.body[0]
			url_shape = canvas.shapeList[0]
			# And it externalizes as a real link because it owns the file data
			assert_that( url_shape.toExternalObject()['url'], is_( links.Link ) )



	@WithSharedApplicationMockDS
	def test_create_friends_list_content_type(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com/FriendsLists/'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )


		assert_that( res.json_body, has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/FriendsLists/boom%40nextthought.com' ) )

	@WithSharedApplicationMockDS
	def test_create_friends_list_post_user(self):
		# Like the previous test, but _UGDPostView wasn't consistent with where it was setting up the phony location proxies,
		# so we could get different results depending on where we came from
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		assert_that( res.json_body, has_entry( 'href', is_('/dataserver2/users/sjohnson%40nextthought.com/FriendsLists/boom%40nextthought.com' ) ))

		testapp.delete( str(res.json_body['href']), extra_environ=self._make_extra_environ() )

	@WithSharedApplicationMockDS
	def test_post_friendslist_friends_field(self):
		"We can put to ++fields++friends"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user('troy.daley@nextthought.com')
		testapp = TestApp( self.app )
		# Make one
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["steve.johnson@nextthought.com"],"realname":"boom"}'
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )

		now = time.time()

		# Edit it
		data = '["troy.daley@nextthought.com"]'
		path = res.json_body['href'] + '/++fields++friends'

		res = testapp.put( str(path),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'friends', has_item( has_entry( 'Username', 'troy.daley@nextthought.com' ) ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		# the object itself is uncachable as far as HTTP goes
		assert_that( res, has_property( 'last_modified', none() ) )
		# But the last modified value is preserved in the body, and did update
		# when we PUT
		assert_that( res.json_body, has_entry( 'Last Modified', greater_than( now ) ) )

		# We can fetch the object and get the same info
		last_mod = res.json_body['Last Modified']
		href = res.json_body['href']

		res = testapp.get( href, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body,	has_entries( 'Last Modified', last_mod, 'href', href ) )

		# And likewise for the collection
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body['Items'], has_entry( 'boom@nextthought.com',
														has_entries( 'Last Modified', last_mod, 'href', href ) ) )

	@WithSharedApplicationMockDS
	def test_create_update_dynamicfriends_list_content_type(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			_ = self._create_user()
			_ = self._create_user( username='troy.daley@nextthought.com' )

		testapp = TestApp( self.app )
		ext_obj = {
			"ContainerId": "FriendsLists",
			"Username": "boom@nextthought.com",
			"friends":["troy.daley@nextthought.com"],
			"realname":"boom",
			'IsDynamicSharing': True }
		data = json.dumps( ext_obj )

		# The user creates it
		path = '/dataserver2/users/sjohnson@nextthought.com/FriendsLists/'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( 'boom@nextthought.com' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		assert_that( res.json_body, has_entry( 'IsDynamicSharing', True ) )

		# It is visible to the member in a few places
		resolved_member_res = testapp.get( '/dataserver2/ResolveUser/troy.daley@nextthought.com', extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
		resolved_member = resolved_member_res.json_body['Items'][0]

		for k in ('DynamicMemberships', 'following', 'Communities'):
			assert_that( resolved_member, has_entry( k, has_item( has_entry( 'Username', contains_string( 'boom@nextthought.com' ) ) ) ) )

		member_fl_res = testapp.get( '/dataserver2/users/troy.daley@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
		assert_that( member_fl_res.json_body, has_entry( 'Items', has_value( has_entry( 'Username', contains_string( 'boom@nextthought.com' ) ) ) ) )

		# The owner can edit it to remove the membership
		data = '[]'
		path = res.json_body['href'] + '/++fields++friends'

		res = testapp.put( str(path),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.json_body, has_entry( 'friends', [] ) )

		# And it is no longer visible to the ex-member
		resolved_member_res = testapp.get( '/dataserver2/ResolveUser/troy.daley@nextthought.com', extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
		resolved_member = resolved_member_res.json_body['Items'][0]

		for k in ('DynamicMemberships', 'following', 'Communities'):
			assert_that( resolved_member, has_entry( k, does_not( has_item( has_entry( 'Username', contains_string( 'boom@nextthought.com' ) ) ) ) ) )

		member_fl_res = testapp.get( '/dataserver2/users/troy.daley@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
		assert_that( member_fl_res.json_body, has_entry( 'Items', does_not( has_value( has_entry( 'Username', contains_string( 'boom@nextthought.com' ) ) ) ) ) )


	@WithSharedApplicationMockDS
	def test_edit_note_returns_editlink(self):
		"The object returned by POST should have enough ACL to regenerate its Edit link"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '{"body": ["text"]}'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		path = urllib.quote( path )
		res = testapp.put( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( json.loads(res.body), has_entry( 'href', path ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'edit' ) ) ) )

	@WithSharedApplicationMockDS
	def test_like_unlike_note(self):
		"We get the appropriate @@like or @@unlike links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/Objects/%s' % n_ext_id
		path = urllib.quote( path )
		# Initially, unliked, I get asked to like
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( json.loads(res.body),
					 has_entry( 'Links',
								has_item(
									has_entry(
										'href',
										'/dataserver2/Objects/' + urllib.quote( n_ext_id ) + '/@@like' ) ) ) )

		# So I do
		res = testapp.post( path + '/@@like', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to unlike
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 1 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unlike' ) ) ) )

		# Same again
		res = testapp.post( path + '/@@like', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unlike' ) ) ) )

		# And I can unlike
		res = testapp.post( path + '/@@unlike', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )

	@WithSharedApplicationMockDS
	def test_favorite_unfavorite_note(self):
		"We get the appropriate @@favorite or @@unfavorite links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		path = urllib.quote( path )
		# Initially, unliked, I get asked to favorite
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )

		# So I do
		res = testapp.post( path + '/@@favorite', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to unlike
		assert_that( res.status_int, is_( 200 ) )
		# like count doesn't change
		assert_that( res.json_body, has_entry( 'LikeCount',  0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unfavorite' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )

		# Same again
		res = testapp.post( path + '/@@favorite', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unfavorite' ) ) ) )

		# And I can unlike
		res = testapp.post( path + '/@@unfavorite', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )

	@WithSharedApplicationMockDS
	def test_edit_note_sharing_coppa_user(self):
		"Unsigned coppa users cannot share anything after creation"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '["Everyone"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		field_path = path + '/++fields++sharedWith' # The name of the external field

		_ = testapp.put( urllib.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" },
						   status=403	)

	@WithSharedApplicationMockDS
	def test_create_note_sharing_coppa_user(self):
		"Unsigned coppa users cannot share anything at creation"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )


		testapp = TestApp( self.app )
		n = contenttypes.Note()
		n.applicableRange = contentrange.ContentRangeDescription()
		n.containerId = u'tag:nti:foo'

		# Note that we externalize before we attempt to add the sharing data,
		# because the sharingTargets field is externalized in a special way
		ext_object = to_external_object( n )
		ext_object['sharedWith'] = ['Everyone']

		data  = to_json_representation( ext_object )

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/'

		_ = testapp.post( urllib.quote( path ),
						   data,
						   extra_environ=self._make_extra_environ(update_request=True),
						   headers={"Content-Type": "application/json" },
						   status=403	)

	@WithSharedApplicationMockDS
	def test_edit_note_sharing_only(self):
		"We can POST to a specific sub-URL to change the sharing"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '["Everyone"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		field_path = path + '/++fields++sharedWith' # The name of the external field

		res = testapp.put( urllib.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body, has_entry( "sharedWith", has_item( "Everyone" ) ) )

		assert_that( res.json_body, has_entry( 'href', urllib.quote( path ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'edit' ) ) ) )

	def _edit_user_ext_field( self, field, data ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			username = user.username
			user_ext_id = to_external_ntiid_oid( user )

		testapp = TestApp( self.app )

		# This works for both the OID and direct username paths
		for path in ('/dataserver2/Objects/%s' % user_ext_id, '/dataserver2/users/' + username):
			# Both the classic (direct) and the namespace approach
			# ONly the namespace is supported
			for field_segment in ('++fields++' + field, ):
				field_path = path + '/' + field_segment # The name of the external field

				res = testapp.put( urllib.quote( field_path ),
								   data,
								   extra_environ=self._make_extra_environ(),
								   headers={"Content-Type": "application/json" } )
				assert_that( res.status_int, is_( 200 ) )

				with mock_dataserver.mock_db_trans( self.ds ):
					# For the case where we change the password, we have to
					# recreate the user for the next loop iteration to work
					user.password = 'temp001'
		return res

	@WithSharedApplicationMockDS
	def test_edit_user_password_only(self):
		"We can POST to a specific sub-URL to change the password"
		data = json.dumps( {'password': 'newp4ssw0r8', 'old_password': 'temp001' } )
		self._edit_user_ext_field( 'password', data )

	@WithSharedApplicationMockDS
	def test_edit_user_count_only(self):
		"We can POST to a specific sub-URL to change the notification count"

		data = '5'
		self._edit_user_ext_field( 'NotificationCount', data )

	@WithSharedApplicationMockDS
	def test_edit_user_avatar_url(self):
		"We can POST to a specific sub-URL to change the avatarURL"

		data = u'"data:image/gif;base64,R0lGODlhEAAQANUAAP///////vz9/fr7/Pf5+vX4+fP2+PL19/D09uvx8+Xt797o69zm6tnk6Nfi5tLf49Dd483c4cva38nZ38jY3cbX3MTW3MPU2sLT2cHT2cDS2b3R2L3Q17zP17vP1rvO1bnN1LbM1LbL07XL0rTK0bLI0LHH0LDHz6/Gzq7Ezq3EzavDzKnCy6jByqbAyaS+yKK9x6C7xZ66xJu/zJi2wY2uukZncwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAEAAQAAAGekCAcEgsEmvIJNJmBNSEAQHh8GQWn4BBAZHAWm1MsM0AVtTEYYd67bAtGrO4lb1mOB4RyixNb0MkFRh7ADZ9bRMWGh+DhX02FxsgJIMAhhkdISUpjIY2IycrLoxhYBxgKCwvMZRCNRkeIiYqLTAyNKxOcbq7uGi+YgBBADs="'
		res = self._edit_user_ext_field( 'avatarURL', data )
		assert_that( res.json_body, has_entry( 'avatarURL', starts_with( '/dataserver2/' ) ) )

		testapp = TestApp( self.app )

		res = testapp.get( res.json_body['avatarURL'], extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'image/gif' ) )

	@WithSharedApplicationMockDS
	def test_put_data_to_user( self ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			username = user.username
			user_ext_id = to_external_ntiid_oid( user )

		testapp = TestApp( self.app )

		# This works for both the OID and direct username paths
		for path in ('/dataserver2/Objects/%s' % user_ext_id, '/dataserver2/users/' + username):

			data = json.dumps( {"NotificationCount": 5 } )

			res = testapp.put( urllib.quote( path ),
							   data,
							   extra_environ=self._make_extra_environ(),
							   headers={"Content-Type": "application/json" } )
			assert_that( res.status_int, is_( 200 ) )
			assert_that( res.json_body, has_entry( 'NotificationCount', 5 ) )


	@WithSharedApplicationMockDS
	def test_get_user_not_allowed(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		testapp.get( path, status=405, extra_environ=self._make_extra_environ())

	@WithSharedApplicationMockDS
	def test_class_provider_hrefs(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			clazz = _create_class( self.ds, ('sjohnson@nextthought.com',) )
			clazz_ntiid = to_external_ntiid_oid( clazz )

		testapp = TestApp( self.app )
		body = testapp.get( '/dataserver2/providers/OU/Classes/CS2051', extra_environ=self._make_extra_environ() )

		body = json.loads( body.text )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.classinfo' ) )
		# The edit href is complete
		assert_that( body, has_entry( 'Links',
									  has_item( has_entries( rel='edit',
															 #href='/dataserver2/providers/OU/Classes/CS2051' ) ) ) )
															 href='/dataserver2/providers/OU/Objects/%s' % urllib.quote(clazz_ntiid) ) ) ) )
		# And the top-level href matches the edit href
		assert_that( body, has_entry( 'href', body['Links'][0]['href'] ) )

		body = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101', extra_environ=self._make_extra_environ() )

		body = json.loads( body.text )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.sectioninfo' ) )
		#assert_that( body, has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101' ) )
		assert_that( body, has_entry( 'href', starts_with( '/dataserver2/providers/OU/Objects/tag' ) ) )

		# We should be able to resolve the parent class of this section
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'rel', 'parent' ) ) ) )
		class_url = body['Links'][0]['href']
		assert_that( class_url, ends_with( 'OU-Class-CS2051' ) ) # NTIID URL
		body = testapp.get( class_url, extra_environ=self._make_extra_environ() )
		json.loads( body.text )

		# When fetched as a collection, they still have edit info

		body = testapp.get( '/dataserver2/providers/OU/Classes/', extra_environ=self._make_extra_environ() )
		body = json.loads( body.text )
		assert_that( body, has_entry( 'href',
									 # '/dataserver2/providers/OU/Objects/%s' % urllib.quote(to_external_ntiid_oid(clazz))))
									  '/dataserver2/providers/OU/Classes' ) )

		assert_that( body, has_entry( 'Items', has_length( 1 ) ) )

		body = body['Items']['CS2051']
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.classinfo' ) )
		# The edit href is complete
		assert_that( body, has_entry( 'Links',
									  has_item( has_entries( rel='edit',
															 #href='/dataserver2/providers/OU/Classes/CS2051' ) ) ) )
															 href='/dataserver2/providers/OU/Objects/%s' % urllib.quote(clazz_ntiid) ) ) ) )
		# And the top-level href matches the edit href
		assert_that( body, has_entry( 'href', body['Links'][0]['href'] ) )


	def _do_post_class_to_path(self, path):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )
		data = json.serialize( { 'Class': 'ClassInfo',  'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2502'} )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2502' ) )


	def _do_post_class_to_path_with_section(self, path, get=None):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )
		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503' } )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101',
											   'Class': 'SectionInfo',  'MimeType': 'application/vnd.nextthought.sectioninfo',
											   'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.put( path + 'CS2503', data, extra_environ=self._make_extra_environ() )

		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

		if get:
			res = testapp.get( path + 'CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

	@WithSharedApplicationMockDS
	def test_post_class_full_path(self):
		self._do_post_class_to_path( '/dataserver2/providers/OU/Classes/' )

	@WithSharedApplicationMockDS
	def test_post_class_full_path_section(self):
		self._do_post_class_to_path_with_section( '/dataserver2/providers/OU/Classes/', get=True )

	@WithSharedApplicationMockDS
	def test_post_class_part_path(self):
		self._do_post_class_to_path( '/dataserver2/providers/OU/' )

	@WithSharedApplicationMockDS
	def test_post_class_section_same_time(self):
		path = '/dataserver2/providers/OU/Classes/'
		get = True
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101',
											   'Class': 'SectionInfo', 'MimeType': 'application/vnd.nextthought.sectioninfo',
											   'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )


		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
		if get:
			res = testapp.get( path + 'CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

	@WithSharedApplicationMockDS
	def test_post_class_section_same_time_uncreated(self):
		path = '/dataserver2/providers/OU/'
		get = True
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			provider = providers.Provider.create_provider( self.ds, username='OU' )
		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101', 'Class': 'SectionInfo', 'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )


		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
		if get:
			res = testapp.get( path + 'Classes/CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

	@WithSharedApplicationMockDS
	def test_share_note_with_class(self):
		"We can share with the NTIID of a class we are enrolled in to get to the other students and instructors."
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )
			self._create_user( username='foo@bar' )

			klass = _create_class( self.ds, ('sjohnson@nextthought.com','jason.madden@nextthought.com') )
			sect = list(klass.Sections)[0]
			sect_ntiid = sect.NTIID
			sect.InstructorInfo.Instructors.append( 'foo@bar' )

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '["' + sect_ntiid + '"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		field_path = path + '/++fields++sharedWith' # The name of the external field

		res = testapp.put( urllib.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'sharedWith', contains_inanyorder( 'foo@bar', 'jason.madden@nextthought.com' ) ) )

	@WithSharedApplicationMockDS
	def test_user_search_returns_enrolled_classes(self):
		"We can find class sections we are enrolled in with a search"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			klass = _create_class( self.ds, ('sjohnson@nextthought.com','jason.madden@nextthought.com') )
			sect = list(klass.Sections)[0]
			sect_name = sect.ID
			sect_ntiid = sect.NTIID

		testapp = TestApp( self.app )

		path = '/dataserver2/UserSearch/' + sect_name

		res = testapp.get( urllib.quote( path ),
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body, has_entry( 'Items', has_item( has_entry( 'Class', 'SectionInfo' ) ) ) )
		sect_info = res.json_body['Items'][0]

		assert_that( sect_info, has_entry( 'Username', sect_ntiid ) )
		assert_that( sect_info, has_entry( 'alias', sect_name ) )
		assert_that( sect_info, has_key( 'avatarURL' ) )


	@WithSharedApplicationMockDSWithChanges
	def test_note_in_feed(self):
		self.ds.add_change_listener( users.onChange )

		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()
			_user2 = self._create_user( username='foo@bar' )

		testapp = TestApp( self.app )
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_HTML, specific='1234' )
		data = json.serialize( { 'Class': 'Note',
								 'MimeType': 'application/vnd.nextthought.note',
								 'ContainerId': containerId,
								 'sharedWith': ['foo@bar'],
								 'selectedText': 'This is the selected text',
								 'body': ["The note body"],
								 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		# And the feed for the other user (not ourself)
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.atom'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/atom+xml'))
		assert_that( res.body, contains_string( "The note body" ) )
		#atom_res = res

		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.rss'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/rss+xml'))
		assert_that( res.content_type_params, has_entry( 'charset', 'utf-8' ) )
		assert_that( res.body, contains_string( "The note body" ) )

		#res._use_unicode = False # otherwise lxml complains when given a Unicode string to decode
		#pq = res.pyquery

		# We can deal with last modified requests (as is common in fead readers)
		# by returning not modified
		testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'),
					 headers={'If-Modified-Since': res.headers['Last-Modified']},
					 status=304	)




class TestApplicationSearch(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_search_empty_term_user_ugd_book(self):
		"Searching with an empty term returns empty results"
		with mock_dataserver.mock_db_trans( self.ds ):
			contained = ContainedExternal()
			user = self._create_user()
			user2 = self._create_user('foo@bar')
			user2_username = user2.username
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		# The results are not defined across the search types,
		# we just test that it doesn't raise a 404
		for search_path in ('users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData',):
			for ds_path in ('dataserver2',):
				path = '/' + ds_path +'/' + search_path + '/'
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )

				# And access is not allowed for a different user
				testapp.get( path, extra_environ=self._make_extra_environ(user=user2_username), status=403)
				# Nor one that doesn't exist
				testapp.get( path, extra_environ=self._make_extra_environ(user='user_dne@biz'), status=401)

	@WithSharedApplicationMockDS
	def test_ugd_search_no_data_returns_empty(self):
		"Any search term against a user whose index DNE returns empty results"
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		for search_term in ('', 'term'):
			for ds_path in ('dataserver2', ):
				path = '/' + ds_path +'/users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData/' + search_term
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )

		# This should not have created index entries for the user.
		# (Otherwise, theres denial-of-service possibilities)
		with _trivial_db_transaction_cm():
			ixman = pyramid.config.global_registries.last.getUtility( nti.contentsearch.interfaces.IIndexManager )
			assert_that( ixman._get_user_index_manager( 'user@dne.org', create=False ), is_( none() ) )
			assert_that( ixman._get_user_index_manager( 'sjohnson@nextthought.com', create=False ), is_( none() ) )

	@WithSharedApplicationMockDS
	def test_ugd_search_other_user(self):
		"Security prevents searching other user's data"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()


		testapp = TestApp( self.app )
		for search_term in ('', 'term'):
			for ds_path in ('dataserver2',):
				path = '/' + ds_path +'/users/user@dne.org/Search/RecursiveUserGeneratedData/' + search_term
				testapp.get( path, extra_environ=self._make_extra_environ(), status=404)


		# This should not have created index entries for the user.
		# (Otherwise, there's denial-of-service possibilities)
		ixman = pyramid.config.global_registries.last.getUtility( nti.contentsearch.interfaces.IIndexManager )
		with _trivial_db_transaction_cm():
			assert_that( ixman._get_user_index_manager( 'user@dne.org', create=False ), is_( none() ) )
			assert_that( ixman._get_user_index_manager( 'sjohnson@nextthought.com', create=False ), is_( none() ) )


	@WithSharedApplicationMockDSWithChanges
	def test_post_share_delete_highlight(self):
		self.ds.add_change_listener( users.onChange )
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()
			self._create_user( username='foo@bar' )
			testapp = TestApp( self.app )
			containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			data = json.serialize( { 'Class': 'Highlight', 'MimeType': 'application/vnd.nextthought.highlight',
									 'ContainerId': containerId,
									 'selectedText': "This is the selected text",
									 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		href = res.json_body['href']
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + containerId + ')/UserGeneratedData'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )

		# I can share the item
		path = href + '/++fields++sharedWith'
		data = json.dumps( ['foo@bar'] )
		res = testapp.put( str(path), data, extra_environ=self._make_extra_environ() )
		assert_that( res.json_body, has_entry( 'sharedWith', ['foo@bar'] ) )

		# And the recipient can see it
		path = '/dataserver2/users/foo@bar/Pages(' + containerId + ')/UserGeneratedData'
		res = testapp.get( str(path), extra_environ=self._make_extra_environ(user=b'foo@bar'))
		assert_that( res.body, contains_string( "This is the selected text" ) )

		# I can now delete that item
		testapp.delete( str(href), extra_environ=self._make_extra_environ())

		# And it is no longer available
		res = testapp.get( str(path), extra_environ=self._make_extra_environ(user=b'foo@bar'),
						   status=404)



def _create_class(ds, usernames_to_enroll=()):
	provider = providers.Provider.create_provider( ds, username='OU' )
	klass = provider.maybeCreateContainedObjectWithType(  'Classes', None )
	klass.containerId = u'Classes'
	klass.ID = 'CS2051'
	klass.Description = 'CS Class'
	mock_dataserver.current_transaction.add( klass )
	#with mock_dataserver.mock_db_trans(ds) as txn:
	#	txn.add( klass )

	section = classes.SectionInfo()
	section.ID = 'CS2051.101'
	section.creator = provider
	klass.add_section( section )
	section.InstructorInfo = classes.InstructorInfo()
	for user in usernames_to_enroll:
		section.enroll( user )
	section.InstructorInfo.Instructors.append( 'jason.madden@nextthought.com' )
	section.InstructorInfo.Instructors.append( 'sjohnson@nextthought.com' )
	section.Provider = 'OU'
	provider.addContainedObject( klass )

	assert_that( provider, has_property( '__parent__', ds.root['providers'] ) )
	return klass

class TestApplicationLibraryBase(ApplicationTestBase):
	_check_content_link = True
	_stream_type = 'Stream'
	child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='HTML' )

	def _setup_library(self, content_root='/prealgebra/', lastModified=None):
		test_self = self
		class NID(object):
			interface.implements( lib_interfaces.IContentUnit )
			ntiid = test_self.child_ntiid
			href = 'sect_0002.html'
			__parent__ = None
			__name__ = 'The name'
			def with_parent( self, p ):
				self.__parent__ = p
				return self

		class LibEnt(object):
			interface.implements( lib_interfaces.IContentPackage )
			root = content_root
			ntiid = None
			__parent__ = None


		if lastModified is not None:
			NID.lastModified = lastModified
			LibEnt.lastModified = lastModified

		class Lib(object):
			interface.implements( lib_interfaces.IContentPackageLibrary )
			titles = ()

			def __getitem__(self, key):
				if key != test_self.child_ntiid:
					raise KeyError( key )
				return NID().with_parent( LibEnt() )

			def pathToNTIID( self, ntiid ):
				return [NID().with_parent( LibEnt() )] if ntiid == test_self.child_ntiid else None

		return Lib()


	def test_library_accept_json(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		for accept_type in ('application/json','application/vnd.nextthought.pageinfo','application/vnd.nextthought.pageinfo+json'):

			res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
							   headers={"Accept": accept_type},
							   extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 200 ) )

			assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
			assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
			if self._check_content_link:
				assert_that( res.json_body, has_entry( 'Links', has_item( all_of( has_entry( 'rel', 'content' ),
																				  has_entry( 'href', '/prealgebra/sect_0002.html' ) ) ) ) )

			assert_that( res.json_body, has_entry( 'Links', has_item( all_of( has_entry( 'rel', self._stream_type ),
																			  has_entry( 'href',
																						 urllib.quote(
																						 '/dataserver2/users/sjohnson@nextthought.com/Pages(' + self.child_ntiid + ')/' + self._stream_type ) ) ) ) ) )


class TestApplicationLibrary(TestApplicationLibraryBase):


	def test_library_redirect(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		# Unauth gets nothing
		testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, status=401 )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )


	def test_library_redirect_with_fragment(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp( self.app )


		fragment = "#fragment"
		ntiid = self.child_ntiid + fragment
		res = testapp.get( '/dataserver2/NTIIDs/' + ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )


	def test_library_accept_link(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": "application/vnd.nextthought.link+json"},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.link+json' ) )
		assert_that( res.json_body, has_entry( 'href', '/prealgebra/sect_0002.html' ) )


	def test_directly_set_page_shared_settings(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			# First, we must put an object so we have a container
			note = contenttypes.Note()
			note.containerId = self.child_ntiid
			user.addContainedObject( note )

		# Ensure we have modification dates on our _NTIIDEntries
		# so that our trump behaviour works as expected
		self.config.registry.registerUtility( self._setup_library(lastModified=1000) )
		accept_type = 'application/json'
		testapp = TestApp( self.app )
		# To start with, there is no modification info
		res = testapp.get( str('/dataserver2/NTIIDs/' + self.child_ntiid),
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( 1000, webob.datetime_utils.UTC ) ) )


		data = json.dumps( {"sharedWith": ["a@b"] } )
		now = datetime.datetime.now(webob.datetime_utils.UTC)
		now = now.replace( microsecond=0 )

		res = testapp.put( str('/dataserver2/NTIIDs/' + self.child_ntiid + '/++fields++sharingPreference'),
						   data,
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		assert_that( res.json_body, has_entry( 'href', '/dataserver2/Objects/' + self.child_ntiid ) )
		# Now there is modification
		assert_that( res.last_modified, is_( greater_than_or_equal_to( now ) ) )
		last_mod = res.last_modified
		# And it is maintained
		res = testapp.get( str('/dataserver2/NTIIDs/' + self.child_ntiid),
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( last_mod ) )




class TestApplicationLibraryNoSlash(TestApplicationLibrary):

	def _setup_library(self, *args, **kwargs):
		return super(TestApplicationLibraryNoSlash,self)._setup_library( content_root="prealgebra", **kwargs )

class TestRootPageEntryLibrary(TestApplicationLibraryBase):
	child_ntiid = ntiids.ROOT
	_check_content_link = False
	_stream_type = 'RecursiveStream'

	def test_one_dfl_entry_default_share(self):
		"""If a user is a member of exactly ONE DFL, then that is his default sharing."""
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			u2 = self._create_user( username="user2@nti" )
			fl1 = users.DynamicFriendsList(username='Friends')
			fl1.creator = u2 # Creator must be set

			u2.addContainedObject( fl1 )
			fl1.addFriend( u )

			fl1_ntiid = fl1.NTIID

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": 'application/json' },
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', [fl1_ntiid] ) ) )


	def test_set_root_page_prefs_inherits(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp( self.app )

		# First, put to the root
		now = datetime.datetime.now(webob.datetime_utils.UTC)
		now = now.replace( microsecond=0 )

		accept_type = 'application/json'
		data = json.dumps( {"sharedWith": ["a@b"] } )

		res = testapp.put( str('/dataserver2/NTIIDs/' + ntiids.ROOT + '/++fields++sharingPreference'),
						   data,
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		assert_that( res.json_body, has_entry( 'href', '/dataserver2/Objects/' + ntiids.ROOT ) )

		# Then, reset the library so we have a child, and get the child
		self.child_ntiid = TestApplicationLibrary.child_ntiid
		self.config.registry.registerUtility( self._setup_library() )

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": accept_type },
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		# Now there is modification
		assert_that( res.last_modified, is_( greater_than_or_equal_to( now ) ) )


import nti.appserver._util

def test_dump_stacks():
	seq = nti.appserver._util.dump_stacks()

	assert_that( seq, has_item( contains_string( 'dump_stacks' ) ) )
