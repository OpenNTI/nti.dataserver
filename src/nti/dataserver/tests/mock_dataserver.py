from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)


import ZODB

from ZODB.DemoStorage import DemoStorage
try:
	from ZODB.FileStorage import FileStorage
except ImportError:
	# BTrees._fsBTree is missing usually
	FileStorage = None


import nti.dataserver as dataserver
from nti.dataserver._Dataserver import Dataserver
from nti.dataserver.config import _make_connect_databases

from zope import component
from zope.dottedname import resolve as dottedname

from nti.dataserver import interfaces as nti_interfaces
from nti.testing.base import ConfiguringTestBase as _BaseConfiguringTestBase
from nti.testing.base import SharedConfiguringTestBase as _BaseSharedConfiguringTestBase

from . import mock_redis

class MockConfig(object):
	zeo_conf = None
	zeo_client_conf = None

class ChangePassingMockDataserver(Dataserver ):

	_mock_database = None
	#: A demo storage will be created on top of this
	#: storage. This can be used to create objects at
	#: class or module set up time and have them available
	#: to dataservers created at test method set up time.
	_storage_base = None

	def __init__( self, *args, **kwargs ):
		self._storage_base = kwargs.pop('base_storage',None)
		super(ChangePassingMockDataserver,self).__init__(*args, **kwargs)

	def _setup_conf( self, *args, **kwargs ):
		conf = MockConfig()
		conf.connect_databases = _make_connect_databases(conf)
		return conf

	def _setup_change_distribution( self ):
		return (None, None)

	def _setup_session_manager( self, *args ):
		pass

	def _setup_chat( self, *args ):
		pass

	def _setup_redis( self, *args ):
		client = mock_redis.InMemoryMockRedis()
		component.provideUtility( client )
		return client

	def _setup_cache( self, *args ):
		return None

	def _setup_dbs( self, *args ):
		self.conf.zeo_uris = ["memory://1?database_name=Users&demostorage=true",
							  ]
		self.conf.zeo_launched = True

		if self._mock_database:
			# Replace the connect function with this trivial one
			self.conf.zeo_make_db = lambda: self._mock_database
		else:
			# DemoStorage supports blobs if its 'changes' storage supports blobs or is not given;
			# a plain MappingStorage does not.
			# It might be nice to use TemporaryStorage here for the 'base', but it's incompatible
			# with DemoStorage: It raises a plain KeyError instead of a POSKeyError for missing
			# objects, which breaks DemoStorages' base-to-change handling logic
			# Blobs are used for storing "files", which are used for image data, which comes up
			# in at least evolve25
			self.conf.zeo_make_db = lambda: ZODB.DB( DemoStorage(base=self._storage_base), database_name='Users')

		return super( ChangePassingMockDataserver, self )._setup_dbs( *args )


class MockDataserver(ChangePassingMockDataserver):

	def enqueue_change( self, change, **kwargs ):
		pass


def add_memory_shard( mock_ds, new_shard_name ):
	"""
	Operating within the scope of a transaction, add a new shard with the given
	name to the configuration of the given mock dataserver.
	"""

	new_db = ZODB.DB( DemoStorage(), databases=mock_ds.db.databases, database_name=new_shard_name )

	current_conn = mock_ds.root._p_jar
	installer = dottedname.resolve( 'nti.dataserver.generations.install.install_shard' )

	installer( current_conn, new_db.database_name )

import nose.tools

current_mock_ds = None

from zope.site import LocalSiteManager, SiteManagerContainer
from zope.component.hooks import site
import transaction

import tempfile
import shutil
import os

def _mock_ds_wrapper_for( func,
						  factory=MockDataserver,
						  teardown=None,
						  base_storage=None ):

	def f( *args ):
		global current_mock_ds
		_base_storage = base_storage
		if callable(_base_storage):
			_base_storage = _base_storage( *args )
		# see comments about hooks in WithMockDS
		ds = factory(base_storage=_base_storage)
		current_mock_ds = ds
		sitemanc = SiteManagerContainer()
		sitemanc.setSiteManager( LocalSiteManager(None) )

		with site(sitemanc):
			assert component.getSiteManager() == sitemanc.getSiteManager()
			component.provideUtility( ds, nti_interfaces.IDataserver )
			assert component.getUtility( nti_interfaces.IDataserver )
			try:
				func( *args )
			finally:
				current_mock_ds = None
				ds.close()
				if teardown:
					teardown()

	return nose.tools.make_decorator( func )( f )

def WithMockDS( *args, **kwargs ):
	"""

	:keyword base_storage: Either a storage instance that
		will be used as the underlying storage for DemoStorage,
		thus allowing some state to be reused, or a callable
		taking the same arguments as the the function being
		wrapped that returns a storage.

	"""

	teardown = lambda: None
	if len(args) == 1 and not kwargs:
		# Being used as a plain decorator
		func = args[0]

		return _mock_ds_wrapper_for( func )

	# Being used as a decorator factory
	mock_ds_factory = MockDataserver
	if kwargs.get( 'with_changes', None ):
		mock_ds_factory = ChangePassingMockDataserver

	if 'database' in kwargs:
		database = kwargs.pop('database')
		def factory(*args, **kwargs):
			md = mock_ds_factory.__new__(mock_ds_factory)
			md._mock_database = database
			md.__init__()
			return md
	elif 'temporary_filestorage' in kwargs and kwargs['temporary_filestorage']:

		td = tempfile.mkdtemp()
		teardown = lambda: shutil.rmtree( td, ignore_errors=True )
		def factory(*args, **kmargs):

			databases = {}
			db = ZODB.DB( FileStorage( os.path.join( td, 'data' ), create=True),
						  databases=databases,
						  database_name='Users' )
			md = mock_ds_factory.__new__(mock_ds_factory)
			md._mock_database = db
			md.__init__()
			return md
	elif 'factory' in kwargs:
		factory = kwargs.pop('factory')
	else:
		factory = mock_ds_factory

	return lambda func: _mock_ds_wrapper_for( func, factory, teardown, base_storage=kwargs.get('base_storage') )

current_transaction = None

class mock_db_trans(object):
	"""
	A context manager that returns a connection. Use
	inside a function decorated with :class:`WithMockDSTrans`
	or similar.
	"""

	def __init__(self, ds=None):
		self.ds = ds or current_mock_ds
		self._site_cm = None

	def __enter__(self):
		transaction.begin()
		self.conn = conn = self.ds.db.open()
		global current_transaction
		current_transaction = conn
		sitemanc = conn.root()['nti.dataserver']

		self._site_cm = site( sitemanc )
		self._site_cm.__enter__()
		assert component.getSiteManager() == sitemanc.getSiteManager()
		component.provideUtility( self.ds, nti_interfaces.IDataserver )
		assert component.getUtility( nti_interfaces.IDataserver )

		return conn

	def __exit__(self, t, v, tb):
		result = self._site_cm.__exit__(t, v, tb) # if this raises we're in trouble
		global current_transaction
		body_raised = t is not None
		try:
			try:
				if not transaction.isDoomed():
					transaction.commit()
				else:
					transaction.abort()
			except Exception:
				transaction.abort()
				raise
			finally:
				current_transaction = None
				self.conn.close()
		except Exception:
			# Don't let our exception override the original exception
			if not body_raised:
				raise
			logger.exception("Failed to cleanup trans, but body raised exception too")

		reset_db_caches(self.ds)
		return result

def reset_db_caches(ds=None):
	ds = ds or current_mock_ds or component.queryUtility( nti_interfaces.IDataserver )
	if ds is None:
		return
	# Now, clean all objects out of the DB cache. This
	# simulates a real-world scenario where either multiple
	# connections are in use, or multiple machines, or there is cache
	# pressure. It finds bugs that otherwise would be hidden by
	# using the same object across transactions when the cache is the same
	ds.db.pool.map( lambda conn: conn.cacheMinimize() ) # the correct way
	#ds.db.pool.map( lambda conn: conn._resetCache() ) # the nuclear way
	#Connection.resetCaches()

def WithMockDSTrans( func ):

	def with_mock_ds_trans( *args, **kwargs ):
		global current_transaction
		global current_mock_ds
		# Previously, we setHooks() here and resetHooks()
		# in the finally block. Setting is fine, and we do have to have
		# them in place to run the ds, but resetting them here
		# interferes with fixtures (layers) that assume they can
		# set the hooks just once, so we musn't reset them.
		# All fixtures now setHooks() before running, so no
		# need to even do that anymore.
		# setHooks()
		ds = MockDataserver() if not getattr( func, 'with_ds_changes', False ) else ChangePassingMockDataserver()
		current_mock_ds = ds

		try:
			with mock_db_trans( ds ):
				func( *args, **kwargs )
		finally:
			current_mock_ds = None
			current_transaction = None
			ds.close()
			# see comments above
			# resetHooks()

	return nose.tools.make_decorator( func )( with_mock_ds_trans )

class _TestBaseMixin(object):
	set_up_packages = (dataserver,)

	@property
	def ds(self):
		return current_mock_ds


class ConfiguringTestBase(_TestBaseMixin,_BaseConfiguringTestBase):
	"""
	A test base that does two things: first, sets up the :mod:`nti.dataserver` module
	during setUp, and second, makes the value of :data:`current_mock_ds` available
	as a property on this object (when used inside a function decorated with :func:`WithMockDS`
	or :func:`WithMockDSTrans`).
	"""


class SharedConfiguringTestBase(_TestBaseMixin,_BaseSharedConfiguringTestBase):
	"""
	A test base that does two things: first, sets up the :mod:`nti.dataserver` module
	during class setup, and second, makes the value of :data:`current_mock_ds` available
	as a property on this object (when used inside a function decorated with :func:`WithMockDS`
	or :func:`WithMockDSTrans`).
	"""

from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin
from nti.testing.layers import find_test

class DSInjectorMixin(object):

	@classmethod
	def setUpTestDS(cls, test=None):
		test = test or find_test()
		if isinstance(type(test), type) and 'ds' not in type(test).__dict__:
			type(test).ds = _TestBaseMixin.ds


class DataserverTestLayer(ZopeComponentLayer,
						  ConfiguringLayerMixin,
						  DSInjectorMixin):
	"""
	A test layer that does two things: first, sets up the
	:mod:`nti.dataserver` module during class setup. Second, if the
	test instance and test class have no ``ds`` attribute, a property
	is mixed in to provide access to the the value of
	:data:`current_mock_ds` available as a property on this object
	(when used inside a function decorated with :func:`WithMockDS` or
	:func:`WithMockDSTrans`).
	"""

	set_up_packages = ('nti.dataserver',)

	@classmethod
	def setUp(cls):
		cls.setUpPackages()

	@classmethod
	def tearDown(cls):
		cls.tearDownPackages()
		zope.testing.cleanup.cleanUp()

	@classmethod
	def testSetUp(cls, test=None):
		test = test or find_test()
		cls.setUpTestDS(test)

	@classmethod
	def testTearDown(cls):
		pass

import unittest
class DataserverLayerTest(_TestBaseMixin,unittest.TestCase):
	layer = DataserverTestLayer

SharedConfiguringTestLayer = DataserverTestLayer # bwc

import zope.testing.cleanup
class NotDevmodeSharedConfiguringTestLayer(ZopeComponentLayer,
										   ConfiguringLayerMixin,
										   DSInjectorMixin):
	"""
	A test layer that does two things: first, sets up the
	:mod:`nti.dataserver` module during class setup (with no features). Second, if the
	test instance and test class have no ``ds`` attribute, a property
	is mixed in to provide access to the the value of
	:data:`current_mock_ds` available as a property on this object
	(when used inside a function decorated with :func:`WithMockDS` or
	:func:`WithMockDSTrans`).
	"""

	description = "nti.dataserver is ZCML configured without devmode"

	set_up_packages = ('nti.dataserver',)
	features = ()

	@classmethod
	def setUp(cls):
		cls.setUpPackages()

	@classmethod
	def tearDown(cls):
		cls.tearDownPackages()
		zope.testing.cleanup.cleanUp()

	@classmethod
	def testSetUp(cls, test=None):
		test = test or find_test()
		cls.setUpTestDS(test)

class NotDevmodeDataserverLayerTest(_TestBaseMixin,unittest.TestCase):
	layer = NotDevmodeSharedConfiguringTestLayer
