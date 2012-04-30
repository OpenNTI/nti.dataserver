import unittest
import nti.appserver

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown
from pyramid.testing import DummyRequest


import zope.component as component

from nti.dataserver.tests import mock_dataserver
import nti.tests

class ConfiguringTestBase(nti.tests.ConfiguringTestBase):
	"""
	Attributes:
	self.config A pyramid configurator
	self.request A pyramid request
	"""

	set_up_packages = (nti.appserver,)

	def setUp( self ):
		"""
		:return: The `Configurator`.
		"""

		super(ConfiguringTestBase,self).setUp()
		self.request = DummyRequest()
		self.config = psetUp(registry=component.getGlobalSiteManager(),request=self.request,hook_zca=False)
		self.config.setup_registry()
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
