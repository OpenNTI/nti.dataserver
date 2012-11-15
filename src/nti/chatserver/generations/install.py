from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 1

import BTrees

from zc import intid as zc_intid
from zope.catalog.catalog import Catalog
from zope.catalog.interfaces import ICatalog
from zope.generations.generations import SchemaManager

from nti.chatserver import _index as chat_index
from nti.chatserver import interfaces as chat_interfaces

import logging
logger = logging.getLogger( __name__ )

class _ContentSearchSchemaManager(SchemaManager):
	"A schema manager that we can register as a utility in ZCML."
	def __init__( self ):
		super( _ContentSearchSchemaManager, self ).__init__(generation=generation,
														 	minimum_generation=generation,
														 	package_name='nti.chatserver.generations')

def evolve( context ):
	conn = context.connection
	dataserver_folder = conn.root()['nti.dataserver']
	install_meeting_catalog(dataserver_folder)

def install_meeting_catalog( dataserver_folder ):
	
	lsm = dataserver_folder.getSiteManager()
	intids =  lsm.getUtility(zc_intid.IIntIds )
	
	catalog = Catalog()
	catalog.__name__ = '++etc++meeting-catalog'
	catalog.__parent__ = dataserver_folder
	intids.register( catalog )

	lsm.registerUtility( catalog, provided=ICatalog, name=chat_interfaces.MEETING_CATALOG_NAME )

	for name, clazz in ( ('creator', chat_index.CreatorIndex), 
						 ('roomid', chat_index.RoomIdIndex),
						 ('created', chat_index.CreatedDateIndex),
						 ('moderated', chat_index.ModeratedIndex)):
		index = clazz( family=BTrees.family64 )
		intids.register( index )
		catalog[name] = index
		
	return catalog
