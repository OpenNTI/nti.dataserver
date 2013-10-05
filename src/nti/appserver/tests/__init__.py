import nti.appserver

import zope.deferredimport
zope.deferredimport.initialize()

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import none
from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

from nti.testing.base import ConfiguringTestBase as _ConfiguringTestBase
from nti.testing.base import SharedConfiguringTestBase as _SharedConfiguringTestBase

import nti.deprecated # Increase warning verbosity
assert nti.deprecated
from nti.app.testing.request_response import DummyRequest
from nti.app.testing.testing import TestMailDelivery
from nti.app.testing.testing import ITestMailDelivery


_old_pw_manager = None
def setUpPackage():
	from nti.dataserver.users import Principal
	global _old_pw_manager
	# By switching from the very secure and very expensive
	# bcrypt default, we speed application-level tests
	# up (due to faster principal creation and faster password authentication)
	# The forum tests go from 55s to 15s
	# This is a nose1 feature and will have to be moved for nose2,
	# probably to layers (which is a good thing in general)
	_old_pw_manager = Principal.password_manager_name
	Principal.password_manager_name = 'Plain Text'

def tearDownPackage():
	if _old_pw_manager:
		from nti.dataserver.users import Principal
		Principal.password_manager_name = _old_pw_manager

import pyramid.interfaces


import zope.component as component

from nti.dataserver.tests import mock_dataserver
import nti.testing.base



from nti.appserver import z3c_zpt



import webtest.app
import webtest.utils

def _create_request( self, request_factory, request_args ):
	self.request = request_factory( *request_args )
	if request_factory is DummyRequest:
		# See the WebTest 'Framework Hooks' documentation
		self.request.environ['paste.testing'] = True
		self.request.environ['paste.testing_variables'] = {}

		if 'REQUEST_METHOD' not in self.request.environ:
			# req'd by repoze.who 2.1
			self.request.environ['REQUEST_METHOD'] = 'UNKNOWN'

from nti.app.testing.matchers import has_permission as _has_permission
from nti.app.testing.matchers import doesnt_have_permission as _doesnt_have_permission

class _TestBaseMixin(object):
	set_up_packages = (nti.appserver,)
	set_up_mailer = True
	config = None
	request = None

	def beginRequest( self, request_factory=DummyRequest, request_args=() ):
		_create_request( self, request_factory, request_args )
		self.config.begin( request=self.request )

	def get_ds(self):
		"Convenience for when you have imported mock_dataserver and used @WithMockDS/Trans"
		return getattr( self, '_ds', mock_dataserver.current_mock_ds )

	def set_ds(self,ds):
		"setable for backwards compat"
		self._ds = ds
	ds = property( get_ds, set_ds )

	def has_permission( self, permission ):
		return _has_permission( permission, self.request )

	def doesnt_have_permission( self, permission ):
		return _doesnt_have_permission( permission, self.request )


	def link_with_rel( self, ext_obj, rel ):
		for lnk in ext_obj.get( 'Links', () ):
			if lnk['rel'] == rel:
				return lnk

	def link_href_with_rel( self, ext_obj, rel ):
		link = self.link_with_rel( ext_obj, rel )
		if link:
			return link['href']

	def require_link_href_with_rel( self, ext_obj, rel ):
		link = self.link_href_with_rel( ext_obj, rel )
		__traceback_info__ = ext_obj
		assert_that( link, is_not( none() ), rel )
		return link

	def forbid_link_with_rel( self, ext_obj, rel ):
		link = self.link_with_rel( ext_obj, rel )
		__traceback_info__ = ext_obj, link, rel
		assert_that( link, is_( none() ), rel )


TestBaseMixin = _TestBaseMixin
class ConfiguringTestBase(_TestBaseMixin,_ConfiguringTestBase):
	"""
	Attributes:
	self.config A pyramid configurator. Note that it does not have a
		package associated with it.
	self.request A pyramid request
	"""

	def setUp( self, pyramid_request=True, request_factory=DummyRequest, request_args=() ):
		"""
		:return: The `Configurator`, which is also in ``self.config``.
		"""

		super(ConfiguringTestBase,self).setUp()

		if pyramid_request:
			_create_request( self, request_factory, request_args )

		self.config = psetUp(registry=component.getGlobalSiteManager(),request=self.request,hook_zca=False)
		self.config.setup_registry()
		if pyramid_request and not getattr( self.request, 'registry', None ):
			self.request.registry = component.getGlobalSiteManager()

		if self.set_up_mailer:
			# Must provide the correct zpt template renderer or the email process blows up
			# See application.py
			self.config.include('pyramid_chameleon')
			self.config.include('pyramid_mako')

			component.provideUtility( z3c_zpt.renderer_factory, pyramid.interfaces.IRendererFactory, name=".pt" )
			mailer = TestMailDelivery()
			component.provideUtility( mailer, ITestMailDelivery )

		return self.config

	def tearDown( self ):
		ptearDown()
		super(ConfiguringTestBase,self).tearDown()
from nti.appserver import pyramid_authorization
class SharedConfiguringTestBase(_TestBaseMixin,_SharedConfiguringTestBase):

	HANDLE_GC = True # Must do GCs for ZCA cleanup. See superclass

	_mailer = None

	security_policy = None

	@classmethod
	def setUpClass( cls, request_factory=DummyRequest, request_args=(), security_policy_factory=None, force_security_policy=True ):
		"""
		:return: The `Configurator`, which is also in ``self.config``.
		"""

		super(SharedConfiguringTestBase,cls).setUpClass()

		cls.config = psetUp(registry=component.getGlobalSiteManager(),request=cls.request,hook_zca=False)
		cls.config.setup_registry()

		if cls.set_up_mailer:
			# Must provide the correct zpt template renderer or the email process blows up
			# See application.py
			cls.config.include('pyramid_chameleon')
			cls.config.include('pyramid_mako')
			component.provideUtility( z3c_zpt.renderer_factory, pyramid.interfaces.IRendererFactory, name=".pt" )
			cls._mailer = mailer = TestMailDelivery()
			component.provideUtility( mailer, ITestMailDelivery )


		if security_policy_factory:
			cls.security_policy = security_policy_factory()
			for iface in pyramid.interfaces.IAuthenticationPolicy, pyramid.interfaces.IAuthorizationPolicy:
				if iface.providedBy( cls.security_policy ) or force_security_policy:
					component.provideUtility( cls.security_policy, iface )
		return cls.config

	ds = property( lambda s: getattr(mock_dataserver, 'current_mock_ds' ) )

	@classmethod
	def tearDownClass( cls ):
		ptearDown()
		cls._mailer = None
		cls.security_policy = None
		super(SharedConfiguringTestBase,cls).tearDownClass()

	def setUp( self ):
		super(SharedConfiguringTestBase,self).setUp()
		if self._mailer:
			del self._mailer.queue[:]
		return self.config

	def tearDown( self ):
		# Some things have to be done everytime
		pyramid_authorization._clear_caches()
		super(SharedConfiguringTestBase,self).tearDown()

class NewRequestSharedConfiguringTestBase(SharedConfiguringTestBase):

	def setUp( self ):
		result = super(NewRequestSharedConfiguringTestBase,self).setUp()
		self.beginRequest()
		return result
