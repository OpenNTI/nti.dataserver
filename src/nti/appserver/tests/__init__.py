import unittest
import nti.appserver

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown
from pyramid.testing import DummyRequest

from zope.configuration import xmlconfig
import zope.component as component
import zope.testing.cleanup
from nti.dataserver.tests import mock_dataserver

class ConfiguringTestBase(zope.testing.cleanup.CleanUp,unittest.TestCase):
	"""
	Attributes:
	self.config A pyramid configurator
	self.request A pyramid request
	"""

	def setUp( self ):
		"""
		:return: The `Configurator`.
		"""
		self.request = DummyRequest()
		self.config = psetUp(registry=component.getGlobalSiteManager(),request=self.request,hook_zca=False)
		self.config.setup_registry()
		# Notice that the pyramid testing setup
		# FAILS to make the sitemanager a child of the global sitemanager.
		# this breaks the zope component APIs in many bad ways
		#zope.component.getSiteManager().__bases__ = (zope.component.getGlobalSiteManager(),)
		#xmlconfig.XMLConfig( 'configure.zcml', module=dataserver )()
		xmlconfig.file( 'configure.zcml', package=nti.appserver )

		return self.config



	def tearDown( self ):
		ptearDown()
		super(ConfiguringTestBase,self).tearDown()

	def get_ds(self):
		"Convenience for when you have imported mock_dataserver and used @WithMockDS/Trans"
		return getattr( self, '_ds', mock_dataserver.current_mock_ds )

	def set_ds(self,ds):
		"setable for backwards compat"
		self._ds = ds
	ds = property( get_ds, set_ds )
