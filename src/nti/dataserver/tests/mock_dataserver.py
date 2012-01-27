

import ZODB
from ZODB.MappingStorage import MappingStorage
from ZODB.DemoStorage import DemoStorage

import nti.dataserver as dataserver
from nti.dataserver import users

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


def WithMockDS( func ):

	def f( *args ):
		global current_mock_ds
		ds = MockDataserver()
		current_mock_ds = ds
		component.provideUtility( ds )
		try:
			func( *args )
		finally:
			current_mock_ds = None
			ds.close()

	return nose.tools.make_decorator( func )( f )

current_transaction = None

def WithMockDSTrans( func ):

	def f( *args, **kwargs ):
		global current_transaction
		global current_mock_ds
		ds = MockDataserver()
		current_mock_ds = ds
		component.provideUtility( ds )
		try:
			with ds.dbTrans() as ct:
				current_transaction = ct
				func( *args, **kwargs )
		finally:
			current_mock_ds = None
			current_transaction = None
			ds.close()
	return nose.tools.make_decorator( func )( f )


import unittest


from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

from zope import component
from zope.configuration import xmlconfig
import zope.testing.cleanup

class ConfiguringTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):

	def setUp( self ):
		psetUp()
		# Fix the broken hooking
		component.getSiteManager().__bases__ = (component.getGlobalSiteManager(),)
		xmlconfig.file( 'configure.zcml', package=dataserver )

	def tearDown( self ):
		ptearDown()
		super(ConfiguringTestBase,self).tearDown()

	@property
	def ds(self):
		return current_mock_ds
