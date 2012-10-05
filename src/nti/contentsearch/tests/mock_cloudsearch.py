from zope import component
from zope import interface

from whoosh import query
from whoosh import fields
from whoosh import analysis
from whoosh import ramindex

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._cloudsearch_query import adapt_searchon_types

def content_analyzer():
	sw_util = component.queryUtility(search_interfaces.IStopWords) 
	stopwords = sw_util.stopwords() if sw_util else ()
	analyzer = 	analysis.StandardAnalyzer(stoplist=stopwords)
	return analyzer

def create_schema():
	analyzer = content_analyzer()
	schema = fields.Schema( id = fields.ID(stored=True, unique=True),
							version = fields.ID(stored=True, unique=False),
							intid = fields.ID(stored=True, unique=True),
							type = fields.ID(stored=False, unique=False),
							creator = fields.ID(stored=False, unique=False),
							last_modified = fields.NUMERIC(type=float, stored=False),
							ntiid = fields.ID(stored=False, unique=False),
							container_id = fields.ID(stored=False, unique=False),
							username = fields.ID(stored=False, unique=False),
							channel = fields.ID(stored=False, unique=False),
							recipients = fields.TEXT(stored=False, spelling=False, phrase=False),
							shared_with = fields.TEXT(stored=False, spelling=False, phrase=False),
							keywords = fields.TEXT(stored=False, spelling=False, phrase=False),
							references = fields.TEXT(stored=False, spelling=False, phrase=False), 
							content = fields.TEXT(stored=False, spelling=True, phrase=True, analyzer=analyzer))
	return schema
		
_cs_schema = create_schema()		

@interface.implementer(search_interfaces.ICloudSearchQueryParser)
class _MockCloundSearchQueryParser(object):
	
	_schema = _cs_schema
	
	def parse(self, qo, username=None):
		username = username or qo.username
		term = qo.term
		
		if term.endswith('*'):
			term = query.Wildcard("content", term)
		elif term.startswith('"') or term.endswith('"'):
			rex = analysis.RegexTokenizer()
			words = [token.text.lower() for token in rex(unicode(term))]
			term = query.Phrase("content", words)
		else:
			term = query.Term("content", term)
			
		ors=[]
		ands=[term, query.Term("username", unicode(username))]
		searchon = adapt_searchon_types(qo.searchon)
		if searchon:
			for type_name in searchon:
				ors.append(query.Term("type", unicode(type_name)))
			
		if ors:
			ands.append(query.Or(ors))
			
		result = query.And(ands)
		return result
	
@interface.implementer(search_interfaces.ICloudSearchStore)
class _MockCloudSearch(object):

	def __init__( self ):
		self.schema = _cs_schema
		self.index =  ramindex.RamIndex(self.schema)
		
	def exists(self, _id):
		with self.index.searcher() as s:
			doc_number = s.document_number(id=unicode(_id))
			return doc_number is not None
		
	def add(self, _id, version, external):
		data = dict(external)
		data['id'] = unicode(_id)
		data['version'] = unicode(repr(version))
		writer = self.index.writer()
		if not self.exists(_id):
			writer.add_document(**data)
		else:
			writer.update_document(**data)
		writer.commit()
		
	def delete(self, _id, *args, **kwargs):
		writer = self.index.writer()
		writer.delete_by_term(u'id', _id)
		writer.commit()
		
	def search(self, bq, *args, **kwargs):
		result = []
		with self.index.searcher() as s:
			hits = s.search(bq)
			for h in hits:
				data = {}
				entry = {u'id': h['id'], u'data': data, u'version': int(h['version'])}
				data['intid'] = [ h['intid'] ]
				result.append(entry)
		return result

	def commit(self, *args, **kwargs):
		return None
	
	def get_aws_domains(self):
		return ()

	def get_domain(self, domain_name=None):
		return None
	
	def get_document_service(self, domain_name=None):
		return self
	
	def get_search_service(self, domain_name=None):
		return self


	