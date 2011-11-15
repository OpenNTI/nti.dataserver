

from ZODB.MappingStorage import MappingStorage

import nti.dataserver as dataserver

class MockDataserver( dataserver._Dataserver.Dataserver ):

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
		return MappingStorage()

	def _setup_storages( self, *args ):
		return ( self._setup_storage(), self._setup_storage(), self._setup_storage() )

import nose.tools


def WithMockDS( func ):

	def f( *args ):
		ds = MockDataserver()
		try:
			func( *args )
		finally:
			ds.close()
	return nose.tools.make_decorator( func )( f )

def WithMockDSTrans( func ):

	def f( *args ):
		ds = MockDataserver()
		try:
			with ds.dbTrans():
				func( *args )
		finally:
			ds.close()
	return nose.tools.make_decorator( func )( f )


import unittest


from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

from zope import component
from zope.configuration import xmlconfig

class ConfiguringTestBase(unittest.TestCase):

	def setUp( self ):
		psetUp()
		# Fix the broken hooking
		component.getSiteManager().__bases__ = (component.getGlobalSiteManager(),)
		xmlconfig.file( 'configure.zcml', package=dataserver )

	def tearDown( self ):
		ptearDown()
