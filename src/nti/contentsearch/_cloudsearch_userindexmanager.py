import contextlib

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.oids import toExternalOID
from nti.externalization.oids import fromExternalOID
from nti.externalization.externalization import toExternalObject

from nti.contentsearch.exfm.cloudsearch import get_document_service

from nti.contentsearch import interfaces
from nti.contentsearch import QueryObject
from nti.contentsearch import SearchCallWrapper
from nti.contentsearch.interfaces import IUserIndexManagerFactory
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch._repoze_query import parse_query
from nti.contentsearch._repoze_query import is_all_query
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch.common import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)
from nti.contentsearch.common import (NTIID, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS, content_, ngrams_)

import logging
logger = logging.getLogger( __name__ )


class CloudSearchUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username):
		self.username = username

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'CloudSearchUserIndexManager(user=%s)' % self.username

	def get_username(self):
		return self.username
	
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on]
		return search_on or self.store.get_catalog_names(self.username)

	def _get_id(self, data):
		return toExternalOID(data)
	
	def _get_document_service(self, endpoint):
		return get_document_service(endpoint=endpoint)
	
	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		type_name = normalize_type_name(type_name or get_type_name(data))
		data = toExternalObject(data)
		
		with repoze_context_manager():
			catalog = self._get_create_catalog(data, type_name)
			if catalog and _oid:
				docid = self.store.get_or_create_docid_for_address(self.username, _oid)
				catalog.index_doc(docid, data)
		return docid

	def update_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		_oid = self._get_id(data)
		if not _oid: return None
		with repoze_context_manager():
			docid = self.store.docid_for_address(self.username, _oid)
			if docid:
				catalog = self._get_create_catalog(data, type_name)
				catalog.reindex_doc(docid, data)
			else:
				docid = self.index_content(data, type_name)
		return docid

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		_oid = self._get_id(data)
		if not _oid: return None
		with repoze_context_manager():
			docid = self.store.docid_for_address(self.username, _oid)
			if docid:
				catalog = self._get_create_catalog(data, type_name, create=False)
				if catalog: catalog.unindex_doc(docid)
				self.store.remove_docid(self.username, docid)
		return docid

	def remove_index(self, type_name):
		with repoze_context_manager():
			result = self.store.remove_catalog(self.username, type_name)
			return result

	def docid_for_address(self, address):
		with repoze_context_manager():
			docid = self.store.docid_for_address(self.username, address)
			return docid
		
	def get_stored_indices(self):
		names = get_stored_indices(self.username)
		return names
	get_catalog_names = get_stored_indices
			
	def has_stored_indices(self):
		result = has_stored_indices(self.username)
		return result
	
