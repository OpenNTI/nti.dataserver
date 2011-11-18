""" Tests for the dataserver. """

from unittest import defaultTestLoader
from unittest import TextTestRunner
import os

from hamcrest.core.base_matcher import BaseMatcher

class Provides(BaseMatcher):

	def __init__( self, iface ):
		super(Provides,self).__init__( )
		self.iface = iface

	def _matches( self, item ):
		return self.iface.providedBy( item )

	def describe_to( self, description ):
		description.append_text( 'object providing') \
								 .append( self.iface )

def provides( iface ):
	return Provides( iface )

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


class HasAttr(BaseMatcher):

	def __init__( self, attr ):
		super(HasAttr,self).__init__( )
		self.attr = attr
	def _matches(self, item):
		return hasattr( item, self.attr )

	def describe_mismatch( self, item, mismatch_description ):
		mismatch_description.append_description_of( item ).append_text( ' has no attr ').append_text( self.attr )

def has_attr( attr ):
	return HasAttr( attr )

def runner(path, pattern="*.py"):
	suite = defaultTestLoader.discover(path, pattern)
	try:
		runner = TextTestRunner(verbosity=3)
		for test in suite:
			runner.run(test)
	finally:
		pass

def main():
	dirname = os.path.dirname( __file__ )
	if not dirname:
		dirname = '.'
	runner( dirname )

if __name__ == '__main__':
	main()

