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

	def has_permission( self, permission ):
		return HasPermission( True, permission, self.request )

	def doesnt_have_permission( self, permission ):
		return HasPermission( False, permission, self.request )


from pyramid.security import has_permission

class HasPermission(nti.tests.BoolMatcher):

	def __init__( self, value, permission, request ):
		super(HasPermission,self).__init__( value )
		self.permission = permission
		self.request = request

	def _matches(self, item):
		return super(HasPermission,self)._matches( has_permission( self.permission, item, self.request ) )
