

import ZODB

from ZODB.DemoStorage import DemoStorage
from ZODB.FileStorage import FileStorage

import nti.dataserver as dataserver
import nti.dataserver._Dataserver


from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.tests import ConfiguringTestBase as _BaseConfiguringTestBase

from . import mock_redis

class ChangePassingMockDataserver(dataserver._Dataserver.Dataserver ):

	_mock_database = None

	def __init__( self, *args, **kwargs ):
		super(ChangePassingMockDataserver,self).__init__(*args, **kwargs)

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

	def _setup_storage( self, *args ):
		# DemoStorage supports blobs, a plain MappingStorage does not.
		return DemoStorage()

	def _setup_dbs( self, *args ):
		self.conf.zeo_uris = ["memory://1?database_name=Users&demostorage=true",
							  ]
		self.conf.zeo_launched = True
		def make_db():
			databases = {}
			db = ZODB.DB( DemoStorage(), databases=databases, database_name='Users' )
			return db

		self.conf.zeo_make_db = make_db
		if self._mock_database:
			self.conf.connect_databases = lambda: (self._mock_database.databases['Users'], None, None )
		return super( ChangePassingMockDataserver, self )._setup_dbs( *args )

#	def _setup_storages( self, *args ):
#		return ( self._setup_storage(), self._setup_storage(), self._setup_storage() )

	#def _setupPresence( self ):
	#	def getPresence( s ):
	#		return "Online"

	#	users.User.presence = property(getPresence)

class MockDataserver(ChangePassingMockDataserver):

	def enqueue_change( self, change, **kwargs ):
		pass

from zope.dottedname import resolve as dottedname
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
from zope.component.hooks import site, setHooks, resetHooks, getSite, setSite
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

@contextlib.contextmanager
def mock_db_trans(ds=None):
	global current_transaction
	if ds is None:
		ds = current_mock_ds
	transaction.begin()
	conn = ds.db.open()
	current_transaction = conn
	sitemanc = conn.root()['nti.dataserver']

	with site( sitemanc ):
		assert component.getSiteManager() == sitemanc.getSiteManager()
		component.provideUtility( ds, nti_interfaces.IDataserver )
		assert component.getUtility( nti_interfaces.IDataserver )

		yield conn
		transaction.commit()
		conn.close()

class faster_mock_db_trans(object):
	# The class version is moderately faster than the contextlib decorated version,
	# which is important in benchmarks, but the code is more baroque and possibly
	# bug prone
	def __init__( self, ds=None ):
		self._ds = ds
		self._old_site = None
		self._conn = None

	def __enter__( self ):
		ds = self._ds
		if ds is None:
			ds = current_mock_ds
		transaction.begin()
		conn = ds.db.open()
		self._conn = conn
		global current_transaction
		current_transaction = conn
		sitemanc = conn.root()['nti.dataserver']

		self._old_site = getSite()
		setSite(sitemanc)

		assert component.getSiteManager() == sitemanc.getSiteManager()
		component.provideUtility( ds, nti_interfaces.IDataserver )
		assert component.getUtility( nti_interfaces.IDataserver )

		return conn

	def __exit__( self, t, v, tb ):
		try:
			if t is None:
				transaction.commit()
				self._conn.close()
		finally:
			setSite( self._old_site )


current_transaction = None

def WithMockDSTrans( func ):

	def with_mock_ds_trans( *args, **kwargs ):
		global current_transaction
		global current_mock_ds
		ds = MockDataserver()
		current_mock_ds = ds
		transaction.begin()
		conn = ds.db.open()
		current_transaction = conn
		sitemanc = conn.root()['nti.dataserver']
		setHooks()

		with site( sitemanc ):
			assert component.getSiteManager() == sitemanc.getSiteManager()
			component.provideUtility( ds, nti_interfaces.IDataserver )
			assert component.getUtility( nti_interfaces.IDataserver )

			try:
				func( *args, **kwargs )
			finally:
				current_mock_ds = None
				current_transaction = None
				ds.close()
				resetHooks()

	return nose.tools.make_decorator( func )( with_mock_ds_trans )



class ConfiguringTestBase(_BaseConfiguringTestBase):
	"""
	A test base that does two things: first, sets up the :mod:`nti.dataserver` module
	during setUp, and second, makes the value of :data:`current_mock_ds` available
	as a property on this object (when used inside a function decorated with :func:`WithMockDS`
	or :func:`WithMockDSTrans`).
	"""
	set_up_packages = (dataserver,)

	@property
	def ds(self):
		return current_mock_ds
