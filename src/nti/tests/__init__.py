""" Tests for the dataserver. """

import os
import subprocess
import sys

from hamcrest.core.base_matcher import BaseMatcher
import hamcrest

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
	pass


from zope import component
from zope.configuration import xmlconfig
from zope.component.hooks import setHooks, resetHooks

class ConfiguringTestBase(AbstractTestBase):
	set_up_packages = ()
	def setUp( self ):
		super(ConfiguringTestBase,self).setUp()
		setHooks()
		# zope.component.globalregistry conveniently adds
		# a zope.testing.cleanup.CleanUp to reset the globalSiteManager
		for i in self.set_up_packages:
			xmlconfig.file( 'configure.zcml', package=i )

	def tearDown( self ):
		resetHooks()
		super(ConfiguringTestBase,self).tearDown()



def main():
	dirname = os.path.dirname( __file__ )
	if not dirname:
		dirname = '.'
	pardirname = os.path.join( dirname, '..' )
	pardirname = os.path.abspath( pardirname )
	for moddir in os.listdir( pardirname ):
		testfile = os.path.join( pardirname, moddir, 'tests', '__main__.py' )
		if os.path.exists( testfile ):
			print testfile
			env = dict(os.environ)
			path = list(sys.path)
			path.insert( 0, pardirname )
			env['PYTHONPATH'] = os.path.pathsep.join( path )
			subprocess.call( [sys.executable, testfile], env=env )

if __name__ == '__main__':
	main()
