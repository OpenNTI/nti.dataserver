import unittest
import nti.appserver

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

from zope.configuration import xmlconfig
import zope.component

class ConfiguringTestBase(unittest.TestCase):

	def setUp( self ):
		psetUp()
		# Notice that the pyramid testing setup
		# FAILS to make the sitemanager a child of the global sitemanager.
		# this breaks the zope component APIs in many bad ways
		zope.component.getSiteManager().__bases__ = (zope.component.getGlobalSiteManager(),)
		#xmlconfig.XMLConfig( 'configure.zcml', module=dataserver )()
		xmlconfig.file( 'configure.zcml', package=nti.appserver )




	def tearDown( self ):
		ptearDown()
