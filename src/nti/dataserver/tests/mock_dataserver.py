
import warnings
import ZODB
from ZODB.MappingStorage import MappingStorage
from ZODB.DemoStorage import DemoStorage

import nti.dataserver as dataserver
import nti.dataserver._Dataserver
from nti.dataserver import users

from zope import component
from ZODB.DB import ContextManager as DBContext
from nti.dataserver import interfaces as nti_interfaces


class MockDataserver( dataserver._Dataserver.Dataserver ):

	def __init__( self, *args, **kwargs ):
		super(MockDataserver,self).__init__(*args, **kwargs)


	def enqueue_change( self, change, **kwargs ):
		pass

	def _setup_change_distribution( self ):
		return (None, None)

	def _setup_session_manager( self, *args ):
		pass

	def _setup_chat( self, *args ):
		pass

	def _setup_apns( self, *args ):
		pass

	def _setup_storage( self, *args ):
		# DemoStorage supports blobs, a plain MappingStorage does not.
		return DemoStorage()

	def _setup_dbs( self, *args ):
		self.conf.zeo_uris = ["memory://1?database_name=Users&demostorage=true",
							  "memory://2?database_name=Sessions&demostorage=true",
							  "memory://3?database_name=Search&demostorage=true",]
		self.conf.zeo_launched = True
		def make_db():
			databases = {}
			db = ZODB.DB( DemoStorage(), databases=databases, database_name='Users' )
			# db.classFactory = _ClassFactory( classFactory, db.classFactory )

			sessionsDB = ZODB.DB( DemoStorage(),
								  databases=databases,
								  database_name='Sessions')
#			sessionsDB.classFactory = _ClassFactory( classFactory, sessionsDB.classFactory )

			searchDB = ZODB.DB( DemoStorage(),
								databases=databases,
								database_name='Search')
			return db

		self.conf.zeo_make_db = make_db
		return super( MockDataserver, self )._setup_dbs( *args )

#	def _setup_storages( self, *args ):
#		return ( self._setup_storage(), self._setup_storage(), self._setup_storage() )

	def _setupPresence( self ):
		def getPresence( s ):
			return "Online"

		users.User.presence = property(getPresence)

import nose.tools

current_mock_ds = None

from zope.site import LocalSiteManager, SiteManagerContainer
from zope.component.hooks import site, setHooks, resetHooks
import transaction

def WithMockDS( func ):

	def f( *args ):
		global current_mock_ds
		ds = MockDataserver()
		current_mock_ds = ds
		sitemanc = SiteManagerContainer()
		sitemanc.setSiteManager( LocalSiteManager(None) )
		setHooks()


		with site(sitemanc):
			assert component.getSiteManager() == sitemanc.getSiteManager()
			component.provideUtility( ds )
			assert component.getUtility( nti_interfaces.IDataserver )
			try:
				func( *args )
			finally:
				current_mock_ds = None
				ds.close()
				resetHooks()

	return nose.tools.make_decorator( func )( f )

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
		component.provideUtility( ds )
		assert component.getUtility( nti_interfaces.IDataserver )

		yield conn
		transaction.commit()
		conn.close()


current_transaction = None

def WithMockDSTrans( func ):

	def f( *args, **kwargs ):
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
			component.provideUtility( ds )
			assert component.getUtility( nti_interfaces.IDataserver )

			try:
				func( *args, **kwargs )
			finally:
				current_mock_ds = None
				current_transaction = None
				ds.close()
				resetHooks()

	return nose.tools.make_decorator( func )( f )


import unittest


from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown
from pyramid.testing import DummyRequest

from zope import component
from zope.configuration import xmlconfig
import zope.testing.cleanup

class ConfiguringTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):

	def setUp( self ):
		self.request = DummyRequest()
		self.config = psetUp(request=self.request,hook_zca=False)
		# Notice that the pyramid testing setup
		# FAILS to make the sitemanager a child of the global sitemanager.
		# this breaks the zope component APIs in many bad ways
		#component.getSiteManager().__bases__ = (component.getGlobalSiteManager(),)
		xmlconfig.file( 'configure.zcml', package=dataserver )

	def tearDown( self ):
		ptearDown()
		super(ConfiguringTestBase,self).tearDown()

	@property
	def ds(self):
		return current_mock_ds
