from __future__ import print_function, unicode_literals

import six
import sys

import zopyxtxng3corelogger
sys.modules["zopyx.txng3.core.logger"] = zopyxtxng3corelogger

from zope.interface import implements
from zope.index.interfaces import IInjection
from zope.index.interfaces import IStatistics
from zope.index.interfaces import IIndexSort
from zope.index.interfaces import IIndexSearch

from zopyx.txng3.core.index import Index
from zopyx.txng3.core.config import DEFAULT_LEXICON
from zopyx.txng3.core.config import DEFAULT_RANKING
from zopyx.txng3.core.config import DEFAULT_ENCODING
from zopyx.txng3.core.config import DEFAULT_ADDITIONAL_CHARS

from repoze.catalog.interfaces import ICatalogIndex
from repoze.catalog.indexes.common import CatalogIndex

import logging
logger = logging.getLogger(__name__)
		
# -----------------------------------

class _Proxy(object):
	def __init__(self, fields, data):
		data =  unicode(str(data)) if data else u''
		for field in fields or []:
			self.__dict__[field] = data

class TextIndexNG3(object):
	implements(IInjection, IIndexSearch, IStatistics)
	
	meta_type = 'TextIndexNG3'
	
	manage_options = (	{'label' : 'Index', 'action': 'manage_workspace'},
						{'label' : 'Vocabulary', 'action' : 'vocabularyform'},
						{'label' : 'Test', 'action' : 'queryform'},
						{'label' : 'Converters', 'action' : 'converters'},
						{'label' : 'Thesaurus', 'action' : 'thesaurus'},
						{'label' : 'Adapters', 'action' : 'adapters'},
	                 )

	query_options = ('query', 'encoding', 'parser', 'language', 'field',
					'autoexpand', 'similarity_ratio',
					'ranking', 'ranking_maxhits', 'thesaurus',
					'search_all_fields')
	
	def __init__(self, iden, use_proxy=False, *args, **kwargs):
		self.id = iden
		self.use_proxy = use_proxy
		self.index = Index(	fields=kwargs.get('fields', [iden]),
							lexicon=kwargs.get('lexicon', DEFAULT_LEXICON),
							storage=kwargs.get('storage', 'txng.storages.term_frequencies'),
							splitter=kwargs.get('splitter', 'txng.splitters.default'),
							autoexpand=kwargs.get('autoexpand', 'off'),
							autoexpand_limit=kwargs.get('autoexpand_limit', 4),
							query_parser=kwargs.get('query_parser', 'txng.parsers.en'),
							use_stemmer=kwargs.get('use_stemmer', False),
							languages=kwargs.get('languages', ('en',)),
							use_stopwords=bool(kwargs.get('use_stopwords')),
							default_encoding=kwargs.get('default_encoding', DEFAULT_ENCODING),
							use_normalizer=bool(kwargs.get('use_normalizer')),
							dedicated_storage=bool(kwargs.get('dedicated_storage', True)),
							index_unknown_languages=bool(kwargs.get('index_unknown_languages', True)),
							ranking=bool(kwargs.get('ranking')),
							ranking_method=kwargs.get('ranking_method', DEFAULT_RANKING),
							splitter_casefolding=bool(kwargs.get('splitter_casefolding', True)),
							splitter_additional_chars=kwargs.get('splitter_additional_chars', DEFAULT_ADDITIONAL_CHARS),
						)

	# --- IInjection --- 
	
	def clear(self):
		self.index.clear()
		
	def index_doc(self, docid, text):
		if self.use_proxy:
			if not text or isinstance(text, six.string_types):
				text = _Proxy(self.fields, text)
		self.index_object(docid, text)

	def unindex_doc(self, docid):
		self.unindex_object(docid)

	# --- IStatistics --- 
	
	def documentCount(self):
		result = []
		for field in self.fields:
			s = self.index.getStorage(field)
			result.append(len(s.getDocIds()))
		return max(result)
	document_count = documentCount
	
	def wordCount(self):
		return self.index_size()
	word_count = wordCount
	
	# --- IIndexSearch --- 
	
	def apply(self, query, *args, **kwargs):
		query = unicode(query or '')			
		results = {}
		rs = self.index.search(query, **kwargs)
		if rs:
			ranked_results = rs.ranked_results
			if ranked_results:
				for docid, rank in ranked_results:
					results[docid] = rank
			else:
				for docid in rs.docids:
					results[docid] = 1.0
					
		return results
		
	def suggest(self, term, threshold=0.75, prefix=-1): 
		lexicon = self.index.getLexicon()
		return lexicon.getSimiliarWords(term=term, threshold=threshold, common_length=prefix) 
	
	# -------------------
	
	def index_object(self, docid, obj, *args, **kwargs):
		result = self.index.index_object(obj, docid)
		return int(result)
	
	def unindex_object(self, docid):
		self.index.unindex_object(docid)
		return 1
	
	def index_size(self):
		return len(self.index.getLexicon())
	
	def get_docids(self):
		result = []
		for i, field in enumerate(self.fields):
			s = self.index.getStorage(field)
			docs = s.getDocIds()
			if i == 0:
				result = docs
			elif i == 1:
				result = set(result)
				result.update(docs)
			else:
				result.update(docs)
		return result
	
	# ---------------
	
	@property
	def title(self):
		return self.id
	
	@property
	def fields(self):
		return self.index.fields
	
	def get_index_source_names(self):
		return self.fields


# -----------------------------------

class CatalogTextIndexNG3(CatalogIndex, TextIndexNG3):
	""" 
	Full-text index.
	Query types supported:
	- Contains
	- DoesNotContain
	- Eq
	- NotEq
	"""

	implements(ICatalogIndex, IIndexSort)

	def __init__(self, field, discriminator=None, *args, **kwargs):
		
		if not isinstance(field, six.string_types):
			raise ValueError('index/catalog field must be a string')
		
		discriminator = discriminator or field
		if not callable(discriminator) and not isinstance(discriminator, six.string_types):
			raise ValueError('discriminator value must be callable or a string')
		
		use_proxy = True
		if 'use_proxy' in kwargs:
			use_proxy = bool(kwargs.pop('use_proxy'))
			
		self.discriminator = discriminator
		self._not_indexed = self.family.IF.Set()
		TextIndexNG3.__init__(self, field, use_proxy, *args, **kwargs)

	# ---------------
	
	@property
	def field(self):
		return self.fields[0]
	
	def suggest(self, term, threshold=0.75, prefix=-1): 
		words = TextIndexNG3.suggest(self, term, threshold, prefix)
		return sorted(words, key=lambda x: x[1], reverse=True)
	
	# ---------------
	
	def sort(self, result, reverse=False, limit=None, sort_type=None):
		if not result:
			return result
	
		if not hasattr(result, 'items'):
			raise TypeError(
					"Unable to sort by relevance because the search "
					"result does not contain weights. To produce a weighted "
					"result, include a text search in the query.")
	
		items = [(weight, docid) for (docid, weight) in result.items()]
		items.sort(reverse=not reverse)
		result = [docid for (weight, docid) in items]
		if limit:
			result = result[:limit]
		return result

	def reindex_doc(self, docid, obj):
		return super(CatalogTextIndexNG3, self).reindex_doc(docid, obj)

	def _indexed(self):
		return self.get_docids()

	def applyContains(self, value, *args, **kwargs):
		return self.apply(value, *args, **kwargs)
	
	applyEq = applyContains

