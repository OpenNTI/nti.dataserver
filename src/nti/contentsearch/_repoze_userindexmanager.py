import re
import contextlib

from zope import component
from zope import interface

from repoze.catalog.query import Contains

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch._repoze_index import get_oid
from nti.contentsearch._repoze_index import get_index_hit
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch.common import (NTIID, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS, content_, ngrams_)

import logging
logger = logging.getLogger( __name__ )

@contextlib.contextmanager
def _context_manager():
	yield component.getUtility( interfaces.IRepozeDataStore )
	
class RepozeUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username):
		self.username = username

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'RepozeUserIndexManager(user=%s)' % self.username

	def get_username(self):
		return self.username
	
	@property
	def store(self):
		return component.getUtility( interfaces.IRepozeDataStore )
	datastore = store
	
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on]
		return search_on

	def _get_hits_from_docids(self, docids, limit=None, query=None, use_word_highlight=True, *args, **kwargs):
		lsm = component.getSiteManager()
		connection = getattr( lsm, '_p_jar', None )
		if not connection:
			logger.warn("SiteManager w/o _p_jar can't do search") 
			return [], 0
		
		lm =  0
		items = []
		for docid in docids:
			_oid = self.store.address_for_docid(self.username, docid)
			try:
				svr_obj = connection[_oid]
				if svr_obj:
					hit = get_index_hit(svr_obj, query=query, use_word_highlight=use_word_highlight, **kwargs)
					if hit:
						items.append(hit)
						lm = max(lm, hit[LAST_MODIFIED])
						if limit and len(items) >= limit:
							break
			except:
				logger.exception("Cannot find object with docid '%s' for user '%s'", docid, self.username)
		return items, lm


	def _do_catalog_query(self, catalog, field, query):
		mo = re.search('([\?\*])', query)
		if mo and mo.start(1) == 0:
			# globbing character return all
			ids = self.store.get_docids(self.username)
			return len(ids), ids
		return catalog.query(Contains(field, query))

	def _do_search(self, field, query, limit=None, use_word_highlight=True, *args, **kwargs):

		query = unicode(query)
		results = empty_search_result(query)
		if not query: return results

		lm = 0
		items = results[ITEMS]
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		with _context_manager():
			search_on = search_on if search_on else self.store.get_catalog_names(self.username)
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				if catalog:
					_, docids = self._do_catalog_query(catalog, field, query)
					hits, hits_lm = self._get_hits_from_docids(	docids,
																limit=limit,
																query=query,
																use_word_highlight=use_word_highlight,
																**kwargs)

					lm = max(lm, hits_lm)
					for hit in hits:
						items[hit[NTIID]] = hit

		results[LAST_MODIFIED] = lm
		results[HIT_COUNT] = len(items)
		return results

	def search(self, query, limit=None, *args, **kwargs):
		results = self._do_search(content_, query, limit, True, *args, **kwargs)
		return results

	def ngram_search(self, query, limit=None, *args, **kwargs):
		results = self._do_search(ngrams_, query, limit, False, *args, **kwargs)
		return results
	quick_search = ngram_search

	def suggest(self, term, limit=None, prefix=None, *args, **kwargs):
		term = unicode(term)
		results = empty_suggest_result(term)
		if not term: return results

		suggestions = set()
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		threshold = kwargs.get('threshold', 0.4999)
		prefix = prefix or len(term)

		with _context_manager():
			search_on = search_on if search_on else self.store.get_catalog_names(self.username)
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				textfield = catalog.get(content_, None)
				if isinstance(textfield, CatalogTextIndexNG3):
					words_t = textfield.suggest(term=term, threshold=threshold, prefix=prefix)
					for t in words_t:
						suggestions.add(t[0])

		suggestions = suggestions[:limit] if limit and limit > 0 else suggestions
		results[ITEMS] = list(suggestions)
		results[HIT_COUNT] = len(suggestions)
		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		if ' ' in query:
			suggestions = []
			result = self.search(query, limit, *args, **kwargs)
		else:
			result = self.suggest(query, limit, *args, **kwargs)
			suggestions = result[ITEMS]
			if suggestions:
				result = self.search(suggestions[0], limit, *args, **kwargs)
			else:
				result = self.search(query, limit, *args, **kwargs)

		result[SUGGESTIONS] = suggestions
		return result

	def _get_create_catalog(self, data, type_name=None, create=True):
		type_name = normalize_type_name(type_name or get_type_name(data))
		catalog = self.store.get_catalog(self.username, type_name)
		if not catalog and create:
			catalog = create_catalog(type_name)
			if catalog:
				self.store.add_catalog(self.username, catalog, type_name)
		return catalog

	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		docid = None
		_oid = get_oid(data)
		with _context_manager():
			catalog = self._get_create_catalog(data, type_name)
			if catalog and _oid:
				docid = self.store.get_or_create_docid_for_address(self.username, _oid)
				catalog.index_doc(docid, data)
		return docid

	def update_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		_oid = get_oid(data)
		if not _oid: return None
		with _context_manager():
			docid = self.store.docid_for_address(self.username, _oid)
			if docid:
				catalog = self._get_create_catalog(data, type_name)
				catalog.reindex_doc(docid, data)
			else:
				docid = self.index_content(data, type_name)
		return docid

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		_oid = get_oid(data)
		if not _oid: return None
		with _context_manager():
			docid = self.store.docid_for_address(self.username, _oid)
			if docid:
				catalog = self._get_create_catalog(data, type_name)
				catalog.unindex_doc(docid)
				self.store.remove_docid(self.username, docid)
		return docid

	def remove_index(self, type_name):
		with _context_manager():
			result = self.store.remove_catalog(self.username, type_name)
			return result

	def docid_for_address(self, address):
		with _context_manager():
			docid = self.store.docid_for_address(self.username, address)
			return docid

# -----------------------------

def ruim_factory(*args, **kwargs):
	def f(username, *fargs, **fkwargs):
		return RepozeUserIndexManager(username)
	return f
