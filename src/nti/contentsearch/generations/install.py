from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 1

from zope.generations.generations import SchemaManager

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import create_repoze_datastore
from nti.contentsearch.interfaces import IRepozeDataStore

class _ContentSearchSchemaManager(SchemaManager):
	"A schema manager that we can register as a utility in ZCML."
	def __init__( self ):
		super( _ContentSearchSchemaManager, self ).__init__(generation=generation,
														 	minimum_generation=generation,
														 	package_name='nti.contentsearch.generations')

def evolve( context ):
	install_search( context )

def install_search( context ):
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	
	
	search_conn = conn.get_connection( 'Search' )
	search_root = search_conn.root()
	repoze_datastore = create_repoze_datastore()
	search_conn.add(repoze_datastore)
	search_root['repoze_datastore'] = repoze_datastore
	lsm.registerUtility( repoze_datastore, provided=IRepozeDataStore )
	
	# FIXME: I don't understand why this is necessary. Why does
	# the PersistentOidResolver sometimes not have a _p_jar?
	rsv = lsm.getUtility( nti_interfaces.IOIDResolver )
	if rsv._p_jar is None:
		rsv._p_jar = conn
	
