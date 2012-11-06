import time
import threading

from zope import component
from zope import interface

from whoosh import query
from whoosh import fields
from whoosh import analysis
from whoosh import ramindex

from nti.contentsearch import _cloudsearch_store
from nti.contentsearch.common import (content_, ngrams_)
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._cloudsearch_query import adapt_searchon_types
from nti.contentsearch.common import (default_ngram_maxsize, default_ngram_minsize) 

def content_analyzer():
	sw_util = component.queryUtility(search_interfaces.IStopWords) 
	stopwords = sw_util.stopwords() if sw_util else ()
	analyzer = 	analysis.StandardAnalyzer(stoplist=stopwords)
	return analyzer

def create_schema():
	analyzer = content_analyzer()	
	minsize, maxsize = (default_ngram_minsize, default_ngram_maxsize)
	
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
							ngrams = fields.NGRAMWORDS(minsize=minsize, maxsize=maxsize, stored=False, at='start'),
							content = fields.TEXT(stored=False, spelling=True, phrase=True, analyzer=analyzer))
	return schema
		
_cs_schema = create_schema()		

@interface.implementer(search_interfaces.ICloudSearchQueryParser)
class MockCloundSearchQueryParser(object):
	
	_schema = _cs_schema
	
	def parse(self, qo, username=None):
		username = username or qo.username
		term = qo.term
		
		if qo.is_prefix_search:
			term = query.Wildcard(content_, term)
		elif qo.is_phrase_search:
			rex = analysis.RegexTokenizer()
			words = [token.text.lower() for token in rex(unicode(term))]
			term = query.Phrase(content_, words)
		else:
			term = query.Term(ngrams_, term)
			
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
	
	
class MockDocumentService(object):
	def __init__( self, index ):
		self.index = index
			
	def exists(self, _id):
		with self.index.searcher() as s:
			doc_number = s.document_number(id=unicode(_id))
			return doc_number is not None	
		
	def add(self, _id, version, external):
		data = dict(external)
		data['id'] = unicode(_id)
		data[ngrams_] = data.get(content_, u'')
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
		
	def commit(self, *args, **kwargs):
		return None
	
class MockSearchService(object):
	def __init__( self, index ):
		self.index = index
			
	def search(self, bq, *args, **kwargs):
		result = []
		with self.index.searcher() as s:
			hits = s.search(bq)
			for h in hits:
				data = {}
				entry = {u'id': h['id'], u'data': data, u'version': int(h['version'])}
				data['intid'] = [ h['intid'] ]
				data['score'] = [h.score or 1.0]
				result.append(entry)
		return result
	
@interface.implementer(search_interfaces.ICloudSearchStore)
class MockCloudSearch(_cloudsearch_store._CloudSearchStore):

	def __init__( self ):
		self.schema = _cs_schema
		self.index = ramindex.RamIndex(self.schema)

	def reset_aws_connection(self, **kwargs):
		pass
	
	def get_aws_domains(self):
		return ()

	def get_domain(self, domain_name=None):
		return None
	
	def get_document_service(self, domain_name=None):
		return MockDocumentService(self.index)
	
	def get_search_service(self, domain_name=None):
		return MockSearchService(self.index)

class MockCloudSearchStorageService(_cloudsearch_store._CloudSearchStorageService):
	
	def _spawn_index_listener(self):
		def read_idx_msgs():
			while not self.stop:
				time.sleep(1)
				if not self.stop:
					self.read_process_index_msgs()
		
		th = threading.Thread(target=read_idx_msgs)
		th.start()
		return th


	