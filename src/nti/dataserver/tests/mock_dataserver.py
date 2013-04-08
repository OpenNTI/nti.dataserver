

import ZODB

from ZODB.DemoStorage import DemoStorage
try:
	from ZODB.FileStorage import FileStorage
except ImportError:
	# BTrees._fsBTree is missing usually
	FileStorage = None
from tempstorage.TemporaryStorage import TemporaryStorage

import nti.dataserver as dataserver
import nti.dataserver._Dataserver
from nti.dataserver.config import _make_connect_databases

from zope import component
from zope.dottedname import resolve as dottedname

from nti.dataserver import interfaces as nti_interfaces
from nti.tests import ConfiguringTestBase as _BaseConfiguringTestBase
from nti.tests import SharedConfiguringTestBase as _BaseSharedConfiguringTestBase

from . import mock_redis

class MockConfig(object):
	zeo_conf = None
	zeo_client_conf = None

class ChangePassingMockDataserver(dataserver._Dataserver.Dataserver ):

	_mock_database = None

	def __init__( self, *args, **kwargs ):
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

	def _setup_apns( self, *args ):
		pass

	def _setup_redis( self, *args ):
		client = mock_redis.InMemoryMockRedis()
		component.provideUtility( client )
		return client

	def _setup_dbs( self, *args ):
		self.conf.zeo_uris = ["memory://1?database_name=Users&demostorage=true",
							  ]
		self.conf.zeo_launched = True
		def make_db():
			databases = {}
			# DemoStorage supports blobs if its 'changes' storage supports blobs or is not given;
			# a plain MappingStorage does not.
			# It might be nice to use TemporaryStorage here for the 'base', but it's incompatible
			# with DemoStorage: It raises a plain KeyError instead of a POSKeyError for missing
			# objects, which breaks DemoStorages' base-to-change handling logic
			# Blobs are used for storing "files", which are used for image data, which comes up
			# in at least evolve25
			NEED_BLOBS = True
			factory = DemoStorage if NEED_BLOBS else TemporaryStorage
			db = ZODB.DB( factory(), databases=databases, database_name='Users' )
			return db

		self.conf.zeo_make_db = make_db
		if self._mock_database:
			self.conf.connect_databases = lambda: (self._mock_database.databases['Users'], None, None )
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
from zope.component.hooks import setHooks
from zope.component.hooks import resetHooks
import transaction

import tempfile
import shutil
import os

def _mock_ds_wrapper_for( func, factory=MockDataserver, teardown=None ):

	def f( *args ):
		global current_mock_ds
		ds = factory()
		current_mock_ds = ds
		sitemanc = SiteManagerContainer()
		sitemanc.setSiteManager( LocalSiteManager(None) )
		setHooks()


		with site(sitemanc):
			assert component.getSiteManager() == sitemanc.getSiteManager()
			component.provideUtility( ds, nti_interfaces.IDataserver )
			assert component.getUtility( nti_interfaces.IDataserver )
			try:
				func( *args )
			finally:
				current_mock_ds = None
				ds.close()
				resetHooks()
				if teardown:
					teardown()

	return nose.tools.make_decorator( func )( f )

def WithMockDS( *args, **kwargs ):

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
		def factory():
			md = mock_ds_factory.__new__(mock_ds_factory)
			md._mock_database = kwargs['database']
			md.__init__()
			return md
	elif 'temporary_filestorage' in kwargs and kwargs['temporary_filestorage']:

		td = tempfile.mkdtemp()
		teardown = lambda: shutil.rmtree( td, ignore_errors=True )
		def factory():

			databases = {}
			db = ZODB.DB( FileStorage( os.path.join( td, 'data' ), create=True),
						  databases=databases,
						  database_name='Users' )
			md = mock_ds_factory.__new__(mock_ds_factory)
			md._mock_database = db
			md.__init__()
			return md
	else:
		def factory():
			return mock_ds_factory()

	return lambda func: _mock_ds_wrapper_for( func, factory, teardown )




import contextlib

current_transaction = None

@contextlib.contextmanager
def mock_db_trans(ds=None):
	global current_transaction
	ds = ds or current_mock_ds

	transaction.begin()
	conn = ds.db.open()
	current_transaction = conn
	sitemanc = conn.root()['nti.dataserver']

	with site( sitemanc ):
		assert component.getSiteManager() == sitemanc.getSiteManager()
		component.provideUtility( ds, nti_interfaces.IDataserver )
		assert component.getUtility( nti_interfaces.IDataserver )

		try:
			yield conn
			if not transaction.isDoomed():
				transaction.commit()
			else:
				transaction.abort()
		except Exception:
			transaction.abort()
			raise
		finally:
			conn.close()
			current_transaction = None

	reset_db_caches(ds)

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
		ds = MockDataserver() if not getattr( func, 'with_ds_changes', False ) else ChangePassingMockDataserver()
		current_mock_ds = ds

		setHooks()
		try:
			with mock_db_trans( ds ):
				func( *args, **kwargs )
		finally:
			current_mock_ds = None
			current_transaction = None
			ds.close()
			resetHooks()

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
