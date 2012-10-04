
from zope import interface

from whoosh import query
from whoosh import fields
from whoosh import ramindex
from whoosh.qparser import QueryParser

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._cloudsearch_query import adapt_searchon_types

def create_schema():
	
	schema = fields.Schema( oid = fields.ID(stored=True, unique=False),
							version = fields.ID(stored=True, unique=False),
							intid = fields.ID(stored=True, unique=False),
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
						

@interface.implementer(search_interfaces.ICloudSearchQueryParser)
class _MockCloundSearchQueryParser(object):
	
	_schema = create_schema()
	
	def parse(self, qo, username=None):
		username = username or qo.username
		
		ors=[]
		ands=[query.Term("content", qo.term), query.Term("username", unicode(username))]
		searchon = adapt_searchon_types(qo.searchon)
		if searchon:
			for type_name in searchon:
				ors.append(query.Term("type", unicode(type_name)))
			
		if ors:
			ands.append(query.Or(ors))
			
		result = query.And(ands)
		return result
	
class MockCloudSearch(object):

	def __init__( self ):
		self.schema = create_schema()
		self.index = ramindex.RamIndex(self.schema)
		
	def exists(self, oid):
		qp = QueryParser("oid", schema=self.schema)
		q = qp.parse(unicode(oid))
		with self.index.searcher() as s:
			results = s.search(q)
			return len(results) > 0
		
	def add(self, _id, version, external):
		data = dict(external)
		data['oid'] = unicode(id)
		data['version'] = unicode(repr(version))
		
		writer = self.index.writer()
		if not self.exists(_id):
			writer.add_document(**data)
		else:
			writer.update_document(**data)
		writer.commit()
		
	def delete(self, _id, *args, **kwargs):
		writer = self.index.writer()
		writer.delete_by_term(u'oid', _id)
		writer.commit()
		
	def search(self, bq, *args, **kwargs):
		result = []
		with self.index.searcher() as s:
			hits = s.search(bq)
			for h in hits:
				data = {}
				entry = {u'id': h['oid'], u'data': data}
				data['intid'] = [ h['intid'] ]
				result.append(entry)
		return result

	