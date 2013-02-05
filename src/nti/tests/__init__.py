""" Tests for the dataserver. """

import os
import subprocess
import sys

logger = __import__( 'logging' ).getLogger(__name__)

from hamcrest.core.base_matcher import BaseMatcher
import hamcrest

# Increase verbosity of deprecations
from nti import deprecated

class BoolMatcher(BaseMatcher):
	def __init__( self, value ):
		super(BoolMatcher,self).__init__()
		self.value = value

	def _matches( self, item ):
		return bool(item) == self.value

	def describe_to( self, description ):
		description.append_text( 'object with bool() value ' ).append( str(self.value) )

	def __repr__( self ):
		return 'object with bool() value ' + str(self.value)

def is_true():
	"""
	Matches an object with the bool value of True.
	"""
	return BoolMatcher(True)

def is_false():
	"""
	Matches an object with the bool() value of False.
	"""
	return BoolMatcher(False)

class Provides(BaseMatcher):

	def __init__( self, iface ):
		super(Provides,self).__init__( )
		self.iface = iface

	def _matches( self, item ):
		return self.iface.providedBy( item )

	def describe_to( self, description ):
		description.append_text( 'object providing') \
								 .append( str(self.iface) )

	def __repr__( self ):
		return 'object providing' + str(self.iface)

def provides( iface ):
	return Provides( iface )

from zope import interface
from zope.interface.verify import verifyObject
from zope.interface.exceptions import Invalid, BrokenImplementation, BrokenMethodImplementation, DoesNotImplement
from zope.schema import getValidationErrors, ValidationError
class VerifyProvides(BaseMatcher):

	def __init__( self, iface ):
		super(VerifyProvides,self).__init__()
		self.iface = iface

	def _matches( self, item ):
		try:
			verifyObject(self.iface, item )
		except Invalid:
			return False
		else:
			return True

	def describe_to( self, description ):
		description.append_text( 'object verifiably providing ' ).append( str(self.iface.__name__) )

	def describe_mismatch( self, item, mismatch_description ):
		x = None
		mismatch_description.append_text( str(type(item))  )
		try:
			verifyObject( self.iface, item )
		except BrokenMethodImplementation as x:
			mismatch_description.append_text( str(x).replace( '\n', '' ) )
		except BrokenImplementation as x:
			mismatch_description.append_text( ' failed to provide attribute "').append_text( x.name ).append_text( '"' )
		except DoesNotImplement as x:
			mismatch_description.append_text( " does not implement the interface; it does implement " ).append_text( str(list(interface.providedBy(item))) )
		except Invalid as x:
			#mismatch_description.append_description_of( item ).append_text( ' has no attr ').append_text( self.attr )
			mismatch_description.append_text( str(x).replace( '\n', '' ) )


def verifiably_provides(iface):
	"Matches if the object provides the correct interface. NOTE: This does NOT test schema compliance."
	return VerifyProvides(iface)

class VerifyValidSchema(BaseMatcher):
	def __init__( self, iface ):
		super(VerifyValidSchema,self).__init__()
		self.iface = iface

	def _matches( self, item ):
		errors = getValidationErrors( self.iface, item )
		return not errors

	def describe_to( self, description ):
		description.append_text( 'object validly providing ' ).append( str(self.iface) )

	def describe_mismatch( self, item, mismatch_description ):
		x = None
		mismatch_description.append_text( str(type(item))  )
		errors = getValidationErrors( self.iface, item )

		for attr, exc in errors:
			try:
				raise exc
			except ValidationError:
				mismatch_description.append_text( ' has attribute "').append_text( attr ).append_text( '" with error "' ).append_text( repr(exc) ).append_text( '"\n\t ' )
			except Invalid as x:
				#mismatch_description.append_description_of( item ).append_text( ' has no attr ').append_text( self.attr )
				mismatch_description.append_text( str(x).replace( '\n', '' ) )

def validly_provides(the_schema):
	"Matches if the object validly provides the given schema (interface)"
	return hamcrest.all_of( verifiably_provides( the_schema ), VerifyValidSchema(the_schema) )

class Implements(BaseMatcher):

	def __init__( self, iface ):
		super(Implements,self).__init__( )
		self.iface = iface

	def _matches( self, item ):
		return self.iface.implementedBy( item )

	def describe_to( self, description ):
		description.append_text( 'object implementing') \
								 .append( self.iface )

def implements( iface ):
	return Implements( iface )

has_attr = hamcrest.library.has_property

import unittest
import zope.testing.cleanup

# Ensure that transactions never last past the boundary
# of a test. If a test begins a transaction and then fails to abort or commit it,
# subsequent uses of the transaction package may find that they are in a bad
# state, unable to clean up resources. For example, the dreaded
# ConnectionStateError: Cannot close a connection joined to a transaction
import transaction
zope.testing.cleanup.addCleanUp( transaction.abort )


class AbstractTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):
	"""
	Base class for testing. Inherits the setup and teardown functions for
	:class:`zope.testing.cleanup.CleanUp`; one effect this has is to cause
	the component registry to be reset after every test.

	.. note:: Do not use this when you use :func:`module_setup` and :func:`module_teardown`,
		as the inherited :meth:`setUp` will undo the effects of the module setup.
	"""
	pass

class AbstractSharedTestBase(unittest.TestCase):
	"""
	Base class for testing that can share most global data (e.g., ZCML configuration) between unit tests.
	This is far more efficient, if the global data is otherwise cleaned up or not mutated between tests.
	"""

	@classmethod
	def setUpClass(cls):
		zope.testing.cleanup.cleanUp()

	@classmethod
	def tearDownClass(cls):
		zope.testing.cleanup.cleanUp()


from zope import component
from zope.configuration import xmlconfig, config
from zope.component.hooks import setHooks, resetHooks
from zope.dottedname import resolve as dottedname

def _configure(self=None, set_up_packages=(), features=('devmode',), context=None):

	# zope.component.globalregistry conveniently adds
	# a zope.testing.cleanup.CleanUp to reset the globalSiteManager

	if set_up_packages:
		logger.debug( "Configuring %s with features %s", set_up_packages, features )
		if context is None:
			context = config.ConfigurationMachine()
			xmlconfig.registerCommonDirectives( context )
		for feature in features:
			context.provideFeature( feature )

		for i in set_up_packages:
			__traceback_info__ = (i, self)
			if isinstance( i, tuple ):
				filename = i[0]
				package = i[1]
			else:
				filename = 'configure.zcml'
				package = i

			if isinstance( package, basestring ):
				package = dottedname.resolve( package )
			context = xmlconfig.file( filename, package=package, context=context )

		return context


class ConfiguringTestBase(AbstractTestBase):
	"""
	Test case that can be subclassed when ZCML configuration is desired.

	This class defines two class level attributes:

	.. py:attribute:: set_up_packages
		A sequence of package objects or strings naming packages. These will be configured, in order, using
		ZCML. The ``configure.zcml`` package from each package will be loaded. Instead
		of a package object, each item can be a tuple of (filename, package); in that case,
		the given file (usually ``meta.zcml``) will be loaded from the given package.

	.. py:attribute:: features
		A sequence of strings to be added as features before loading the configuration. By default,
		this is ``devmode``.

	When the meth:`setUp` method runs, one instance attribute is defined:

	.. py:attribute:: configuration_context
		The :class:`config.ConfigurationMachine` that was used to load configuration data (if any).
		This can be used by individual methods to load more configuration data using
		:meth:`configure_packages` or the methods from :mod:`zope.configuration`


	"""
	set_up_packages = ()
	features = ('devmode',)
	configuration_context = None
	def setUp( self ):
		super(ConfiguringTestBase,self).setUp()
		setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these
		self.configuration_context = self.configure_packages( self.set_up_packages, self.features, self.configuration_context )

	def configure_packages(self, set_up_packages=(), features=(), context=None ):
		self.configuration_context = _configure( self, set_up_packages, features, context or self.configuration_context )
		return self.configuration_context

	def tearDown( self ):
		resetHooks()
		super(ConfiguringTestBase,self).tearDown()

class SharedConfiguringTestBase(AbstractSharedTestBase):
	"""
	Test case that can be subclassed when ZCML configuration is desired.

	This class defines two class level attributes:

	.. py:attribute:: set_up_packages
		A sequence of package objects or strings naming packages. These will be configured, in order, using
		ZCML. The ``configure.zcml`` package from each package will be loaded. Instead
		of a package object, each item can be a tuple of (filename, package); in that case,
		the given file (usually ``meta.zcml``) will be loaded from the given package.

	.. py:attribute:: features
		A sequence of strings to be added as features before loading the configuration. By default,
		this is ``devmode``.

	When the meth:`setUp` method runs, one class attribute is defined:

	.. py:attribute:: configuration_context
		The :class:`config.ConfigurationMachine` that was used to load configuration data (if any).
		This can be used by individual methods to load more configuration data.


	"""
	set_up_packages = ()
	features = ('devmode',)
	configuration_context = None
	@classmethod
	def setUpClass( cls ):
		super(SharedConfiguringTestBase,cls).setUpClass()
		setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these
		cls.configuration_context = cls.configure_packages( cls.set_up_packages, cls.features, cls.configuration_context )

	@classmethod
	def configure_packages(cls, set_up_packages=(), features=(), context=None ):
		cls.configuration_context = _configure( cls, set_up_packages, features, context or cls.configuration_context )
		return cls.configuration_context

	@classmethod
	def tearDownClass( cls ):
		resetHooks()
		super(SharedConfiguringTestBase,cls).tearDownClass()

def module_setup( set_up_packages=(), features=('devmode',)):
	"""
	Either import this as ``setUpModule`` at the module level, or call
	it to perform module level set up from your own function with that name.

	This is an alternative to using :class:`ConfiguringTestBase`; the two should
	generally not be mixed in a module. It can also be used with Nose's `with_setup` function.
	"""
	zope.testing.cleanup.setUp()
	setHooks()
	_configure( set_up_packages=set_up_packages, features=features )

def module_teardown():
	"""
	Either import this as ``tearDownModule`` at the module level, or call
	it to perform module level tear down froum your own function with that name.

	This is an alternative to using :class:`ConfiguringTestBase`; the two should
	generally not be mixed in a module.
	"""

	resetHooks()
	zope.testing.cleanup.tearDown()

# The cleanup that we get by importing just zope.interface and zope.component
# has a problem:
# zope.component installs adapter hooks that cause the use of interfaces
# as functions to direct through the current site manager (as does the global component API).
# This adapter hook is a cached function of an implementation detail of the site manager:
# siteManager.adapters.adapter_hook.
#
# If no site is ever set, this caches the adapter_hook of the globalSiteManager.
#
# When the zope.component cleanup runs, it swizzles out the internals of the
# globalSiteManager by re-running __init__. However, it does not clear the cached
# adapter_hook. Thus, subsequent uses of the adapter hook (interface calls, or use
# of the global component API) continue to use the *old* adapter registry (which is no
# longer easy to access and inspect, especially when the C hook optimizations are in use)
# If any non-ZCML registrations are made (or the next test loads a subset of the ZCML the previous test
# did) then this manifests as strange adapter failures.
#
# This is obviously all implementation detail. So rather than "fix" the problem
# ourself, the solution is to import zope.site.site to ensure that the site gets
# cleaned up and the adapter_hook cache thrown away
# This problem never manifests itself in code that has already imported zope.site,
# and it seems to be an assumption that code that uses zope.component also uses zope.site
# (though we have some code that doesn't explicitly do so)

# This is detailed in test_component_broken.txt
# submitted as https://bugs.launchpad.net/zope.component/+bug/1100501
import zope.site.site


import nose.plugins
class ZopeExceptionLogPatch(nose.plugins.Plugin):
	name = 'zopeexceptionlogpatch'
	score = 1000
	enabled = True # Enabled by default
	def configure(self, options, conf ):
		# Force the logcapture plugin, enabled by default,
		# to use the zope exception formatter.
		import zope.exceptions.log
		import logging
		logging.Formatter = zope.exceptions.log.Formatter

	# Also present failure cases formatted the same way
	def formatError(self, test, exc_info):
		t, v, tb = exc_info
		from zope.exceptions.exceptionformatter import format_exception
		# Despite what the docs say, you do not return the test.
		# see logcapture and failuredetail.
		# Omitting filenames makes things shorter
		# and generally more readable, but when the last part of the traceback
		# is in initializing a module, then the filename is the only discriminator
		formatted_tb = ''.join(format_exception(t, v, tb, with_filenames=False))
		if 'Module None' in formatted_tb:
			formatted_tb = ''.join(format_exception(t, v, tb, with_filenames=True))
		return (t, formatted_tb, None)

	def formatFailure(self, test, exc_info):
		return self.formatError( test, exc_info)

# Zope.mimetype registers hundreds and thousands of objects
# doing that for each test makes them take SO much longer
# Unfortunately, as noted above, zope.testing.cleanup.CleanUp
# installs something to reset the gsm, so it's not possible
# to simply pre-cache like the below:
# try:
# 	import zope.mimetype
# 	_configure( None, (('meta.zcml',zope.mimetype),
# 					   ('meta.zcml',zope.component),
# 					   zope.mimetype) )
# except ImportError:
# 	pass

# Attempting to runaround the testing cleanup by
# using a different base doesn't quite work,
# some things are still using the old one
# globalregistry.base = BaseComponents()

from hamcrest import assert_that
from hamcrest import is_

class TypeCheckedDict(dict):

	def __init__( self, key_class=object, val_class=object ):
		dict.__init__( self )
		self.key_class = key_class
		self.val_class = val_class

	def __setitem__( self, key, val ):
		assert_that( key, is_( self.key_class ) )
		assert_that( val, is_( self.val_class ) )
		dict.__setitem__( self, key, val )

try:
	from pyramid.testing import DummyRequest as _DummyRequest
	from pyramid.response import Response as _Response
	from pyramid.decorator import reify
	class _HeaderList( list ):
		# TODO: Very incomplete, but append is the main method
		# used by webob
		def __init__(self, other=()):
			list.__init__( self )
			for k in other: self.append( k )

		def append( self, k ):
			__traceback_info__ = k
			assert_that( k[0], is_( str ), "Header names must be byte strings" )
			assert_that( k[1], is_( str ), "Header values must be byte strings" )
			list.append( self, k )

	class ByteHeadersResponse(_Response):

		def __init__( self, *args, **kwargs ):
			super(_Response,self).__init__( *args, **kwargs )
			# make the list be right, which is directly assigned to in the
			# super, bypassing the property
			self.headerlist = self._headerlist

		def _headerlist__set( self, value ):
			"Ensure type checking of the headers."
			super(ByteHeadersResponse,self)._headerlist__set( value )
			if not isinstance( self._headerlist, _HeaderList ):
				self._headerlist = _HeaderList( self._headerlist )

		headerlist = property(_Response._headerlist__get, _headerlist__set,
							  _Response._headerlist__del, doc=_Response._headerlist__get.__doc__)



	class ByteHeadersDummyRequest(_DummyRequest):

		def __init__( self, **kwargs ):
			if 'headers' in kwargs:
				old_headers = kwargs['headers']
				headers = TypeCheckedDict( str, str )
				for k, v in old_headers.items():
					headers[k] = v
				kwargs['headers']  = headers
			else:
				kwargs['headers'] = TypeCheckedDict( str, str )
			super(ByteHeadersDummyRequest,self).__init__( **kwargs )

		@reify
		def response( self ):
			return ByteHeadersResponse()
			# NOTE: The super implementation consults the registry to find a factory.

except ImportError:
	pass
