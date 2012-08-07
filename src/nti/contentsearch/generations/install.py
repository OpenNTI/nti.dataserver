from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 12

from zope.generations.generations import SchemaManager

import logging
logger = logging.getLogger( __name__ )

class _ContentSearchSchemaManager(SchemaManager):
	"A schema manager that we can register as a utility in ZCML."
	def __init__( self ):
		super( _ContentSearchSchemaManager, self ).__init__(generation=generation,
														 	minimum_generation=generation,
														 	package_name='nti.contentsearch.generations')

def evolve( context ):
	pass

