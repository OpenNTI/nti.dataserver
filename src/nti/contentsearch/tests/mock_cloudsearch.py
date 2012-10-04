
from whoosh import fields
from whoosh import ramindex
#from whoosh.qparser import QueryParser
#from whoosh.analysis import NgramFilter
#from whoosh.analysis import StandardAnalyzer
#from whoosh.qparser.dateparse import DateParserPlugin
#from whoosh.qparser import (GtLtPlugin, PrefixPlugin, PhrasePlugin)

def create_schema():
	
	schema = fields.Schema(	intid = fields.ID(stored=True, unique=False),
							type = fields.ID(stored=False, unique=False),
							creator = fields.ID(stored=False, unique=False),
							last_modified = fields.NUMERIC(type=float, stored=False),
							ntiid = fields.ID(stored=False, unique=False),
							container_id = fields.ID(stored=False, unique=False),
							username = fields.ID(stored=False, unique=False),
							channel = fields.ID(stored=False, unique=False),
							content = fields.TEXT(stored=False, spelling=True, phrase=True),
							recipients = fields.TEXT(stored=False, spelling=False, phrase=False),
							shared_with = fields.TEXT(stored=False, spelling=False, phrase=False),
							keywords = fields.TEXT(stored=False, spelling=False, phrase=False),
							references = fields.TEXT(stored=False, spelling=False, phrase=False))
	return schema
						

class MockCloudSearch(object):

	def __init__( self ):
		self.schema = create_schema()
		self.index = ramindex.RamIndex(self.schema)
		