import unittest
import nti.appserver
from hamcrest import assert_that
from hamcrest import is_

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown
from pyramid.testing import DummyRequest
import pyramid.interfaces


import zope.component as component
from zope import interface

from nti.dataserver.tests import mock_dataserver
import nti.tests


from pyramid_mailer.interfaces import IMailer
from pyramid_mailer.mailer import DummyMailer as _DummyMailer
from repoze.sendmail.interfaces import IMailDelivery

class ITestMailDelivery(IMailer, IMailDelivery):
	pass

from nti.appserver import z3c_zpt

import webtest.lint
from webtest.lint import check_headers as _orig_check_headers
def unicode_check_headers(headers):
	"""
	Up through at least WebTest 1.4.0, the middleware in webtest.lint
	doesn't ensure that header names and values are bytestrings, but
	this is required (if not in the spec, then in the implementation
	provided in gevent 1.0rc1). This check causes that to happen.
	"""
	_orig_check_headers( headers )
	for k, v in headers:
		assert_that( k, is_( str ), 'Header names must be byte strings' )
		assert_that( v, is_( str ), 'Header values must be byte strings' )

def monkey_patch_check_headers():
	"""
	Patches webtest.lint to use :func:`unicode_check_headers`. This module
	does this on import.
	"""
	if webtest.lint.check_headers.__module__ == 'webtest.lint':
		webtest.lint.check_headers = unicode_check_headers
monkey_patch_check_headers()

def _create_request( self, request_factory, request_args ):
	self.request = request_factory( *request_args )
	if request_factory is DummyRequest:
		# See the WebTest 'Framework Hooks' documentation
		self.request.environ['paste.testing'] = True
		self.request.environ['paste.testing_variables'] = {}

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
		return HasPermission( True, permission, self.request )

	def doesnt_have_permission( self, permission ):
		return HasPermission( False, permission, self.request )

class ConfiguringTestBase(_TestBaseMixin,nti.tests.ConfiguringTestBase):
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
			component.provideUtility( z3c_zpt.renderer_factory, pyramid.interfaces.IRendererFactory, name=".pt" )
			mailer = TestMailDelivery()
			component.provideUtility( mailer, ITestMailDelivery )

		return self.config

	def tearDown( self ):
		ptearDown()
		super(ConfiguringTestBase,self).tearDown()

class SharedConfiguringTestBase(_TestBaseMixin,nti.tests.SharedConfiguringTestBase):

	_mailer = None

	@classmethod
	def setUpClass( self, request_factory=DummyRequest, request_args=() ):
		"""
		:return: The `Configurator`, which is also in ``self.config``.
		"""

		super(SharedConfiguringTestBase,self).setUpClass()

		self.config = psetUp(registry=component.getGlobalSiteManager(),request=self.request,hook_zca=False)
		self.config.setup_registry()

		if self.set_up_mailer:
			# Must provide the correct zpt template renderer or the email process blows up
			# See application.py
			component.provideUtility( z3c_zpt.renderer_factory, pyramid.interfaces.IRendererFactory, name=".pt" )
			self._mailer = mailer = TestMailDelivery()
			component.provideUtility( mailer, ITestMailDelivery )

		return self.config

	ds = property( lambda s: getattr(mock_dataserver, 'current_mock_ds' ) )

	@classmethod
	def tearDownClass( self ):
		ptearDown()
		self._mailer = None
		super(SharedConfiguringTestBase,self).tearDownClass()

	def setUp( self ):
		super(SharedConfiguringTestBase,self).setUp()
		if self._mailer:
			del self._mailer.queue[:]
		return self.config

class NewRequestSharedConfiguringTestBase(SharedConfiguringTestBase):

	def setUp( self ):
		result = super(NewRequestSharedConfiguringTestBase,self).setUp()
		self.beginRequest()
		return result

from pyramid.security import has_permission

class HasPermission(nti.tests.BoolMatcher):

	def __init__( self, value, permission, request ):
		super(HasPermission,self).__init__( value )
		self.permission = permission
		self.request = request

	def _matches(self, item):
		return super(HasPermission,self)._matches( has_permission( self.permission, item, self.request ) )


class TestMailDelivery(_DummyMailer):

	default_sender = 'no-reply@nextthought.com'

	def __init__( self ):
		super(TestMailDelivery,self).__init__()


	def send( self, fromaddr, toaddr, message ):
		#from IPython.core.debugger import Tracer; Tracer()() ## DEBUG ##

		self.queue.append( message )
		message.subject = message.get( 'Subject' ) # compat with pyramid_mailer messages
		message.body = message.get_payload()[0].get_payload()
