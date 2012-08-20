""" Tests for the dataserver. """

import os
import subprocess
import sys

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

from zope.interface.verify import verifyObject
from zope.interface.exceptions import Invalid, BrokenImplementation, BrokenMethodImplementation
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
		description.append_text( 'object verifiably providing' ).append( str(self.iface) )

	def describe_mismatch( self, item, mismatch_description ):
		x = None
		mismatch_description.append_text( '(' + str(type(item)) + ') ' )
		try:
			verifyObject( self.iface, item )
		except BrokenMethodImplementation as x:
			mismatch_description.append_text( str(x).replace( '\n', '' ) )
		except BrokenImplementation as x:
			mismatch_description.append_text( 'failed to provide attribute "').append_text( x.name ).append_text( '"' )
		except Invalid as x:
			#mismatch_description.append_description_of( item ).append_text( ' has no attr ').append_text( self.attr )
			mismatch_description.append_text( str(x).replace( '\n', '' ) )


def verifiably_provides(iface):
	return hamcrest.all_of( provides( iface ), VerifyProvides(iface) )


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

class AbstractTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):
	"""
	Base class for testing. Inherits the setup and teardown functions for
	:class:`zope.testing.cleanup.CleanUp`; one effect this has is to cause
	the component registry to be reset after every test.
	"""
	pass


from zope import component
from zope.configuration import xmlconfig, config
from zope.component.hooks import setHooks, resetHooks
from zope.dottedname import resolve as dottedname

def _configure(self=None, set_up_packages=(), features=('devmode',), context=None):

	# zope.component.globalregistry conveniently adds
	# a zope.testing.cleanup.CleanUp to reset the globalSiteManager
	if set_up_packages:
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
		This can be used by individual methods to load more configuration data.


	"""
	set_up_packages = ()
	features = ('devmode',)
	configuration_context = None
	def setUp( self ):
		super(ConfiguringTestBase,self).setUp()
		setHooks()
		self.configuration_context = self.configure_packages( self.set_up_packages, self.features, self.configuration_context )

	def configure_packages(self, set_up_packages=(), features=(), context=None ):
		self.configuration_context = _configure( self, set_up_packages, features, context or self.configuration_context )
		return self.configuration_context

	def tearDown( self ):
		resetHooks()
		super(ConfiguringTestBase,self).tearDown()

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
