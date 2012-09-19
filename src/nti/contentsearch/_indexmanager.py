from __future__ import print_function, unicode_literals

import six

from zope import component
from zope import interface

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import SearchCallWrapper
from nti.contentsearch._search_query import QueryObject
from nti.contentsearch._indexagent import handle_index_event
from nti.contentsearch import interfaces as seach_interfaces
from nti.contentsearch._datastructures import CaseInsensitiveDict

from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import merge_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch._search_results import merge_suggest_results
from nti.contentsearch._search_results import empty_suggest_and_search_results
from nti.contentsearch._search_results import merge_suggest_and_search_results

import logging
logger = logging.getLogger( __name__ )

class IndexManager(object):
	interface.implements(seach_interfaces.IIndexManager)

	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls, *args, **kwargs)
		return cls.indexmanager

	def __init__(self, bookidx_manager_factory, useridx_manager_adapter, search_pool_size=5, *args, **kwargs):
		self.books = CaseInsensitiveDict()
		self.bookidx_manager_factory = bookidx_manager_factory
		self.useridx_manager_adapter = useridx_manager_adapter

	def __str__( self ):
		return self.__repr__()

	def __repr__( self ):
		return 'IndexManager(books=%s, %s)' % (len(self.books), self.useridx_manager_adapter)

	@property
	def dataserver(self):
		return component.queryUtility( nti_interfaces.IDataserver )

	def get_entity(self, username):
		result = User.get_entity(username, dataserver=self.dataserver)
		return result

	def users_exists(self, username):
		result = self.get_entity(username)
		return result is not None

	def get_user_communities(self, username):
		user = self.get_entity(username)
		result = list(user.communities) if user and hasattr(user, 'communities') else []
		if result and 'Everyone' in result:
			result.remove('Everyone')
		return result

	# -------------------

	@SearchCallWrapper
	def search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		cnt_results = self.content_search(query=query)
		ugd_results = self.user_data_search(query=query)	
		results = merge_search_results(cnt_results, ugd_results)
		logger.debug("Query '%s' returned %s hit(s)" % (query.term, len(results)))
		return results

	@SearchCallWrapper
	def ngram_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		cnt_results = self.content_ngram_search(query=query)
		ugd_results = self.user_data_ngram_search(query=query)	
		results = merge_search_results(cnt_results, ugd_results)
		return results

	@SearchCallWrapper
	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		cnt_results = self.content_suggest_and_search(query=query)
		ugd_results = self.user_data_suggest_and_search(query=query)	
		results = merge_suggest_and_search_results(cnt_results, ugd_results)
		return results

	@SearchCallWrapper
	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		cnt_results = self.content_suggest(query=query)
		ugd_results = self.user_data_suggest(query=query)	
		results = merge_suggest_results(cnt_results, ugd_results)
		return results

	# -------------------

	def get_book_index_manager(self, indexid):
		return self.books.get(indexid, None) if indexid is not None else None

	def add_book(self, indexname, ntiid=None, *args, **kwargs):
		result = False
		indexid = indexname if not ntiid else ntiid
		if not self.books.has_key(indexid):
			bmi = self.bookidx_manager_factory(indexname=indexname, ntiid=ntiid, **kwargs)
			if bmi is not None:
				result = True
				self.books[indexid] = bmi
				logger.info("Book index '%s,%r' has been added to index manager" % (indexname, ntiid))
			else:
				logger.warn("Could not add book index '%s,%r,%r' to index manager" % (indexname, ntiid, kwargs))
		return result

	def content_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexid)
		results = bm.search(query) if (bm is not None and not query.is_empty) else None
		return results if results is not None else empty_search_results(query)

	def content_ngram_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexid)
		results = bm.ngram_search(query) if (bm is not None and not query.is_empty) else None
		return results if results is not None else empty_search_results(query)

	def content_suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexid)
		results = bm.suggest_and_search(query) if (bm is not None and not query.is_empty) else None
		return results if results is not None else empty_suggest_and_search_results(query)

	def content_suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexid)
		results = bm.suggest(query) if (bm is not None and not query.is_empty) else None
		return results if results is not None else empty_suggest_results(query)

	quick_search = content_ngram_search
	content_quick_search = content_ngram_search

	# -------------------

	def _get_user_index_manager(self, target, create=True):
		if isinstance( target, six.string_types ):
			target = self.get_entity( target )
		result = self.useridx_manager_adapter(target, None) if target and create else None
		return result

	def _get_search_uims(self, username):
		result = []
		for name in [username] + self.get_user_communities(username):
			uim = self._get_user_index_manager(name)
			if uim is not None:
				result.append(uim)
		return result

	# -------------------

	####
	# TODO: *args and **kwargs  seem to be way overused, making
	# refactoring very difficult. When arguments are not optional, e.g., 'username'
	# it should be declared.

	def user_data_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = empty_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.search(query=query)
			results = merge_search_results (results, rest)
		return results

	def user_data_ngram_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = empty_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.ngram_search(query=query)
			results = merge_search_results (results, rest)
		return results

	user_data_quick_search = user_data_ngram_search

	def user_data_suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = empty_suggest_and_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest_and_search(query=query)
			results = merge_suggest_and_search_results (results, rest)
		return results
	
	def user_data_suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = empty_suggest_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest(query=query)
			results = merge_suggest_results(results, rest)
		return results

	# -------------------

	def index_user_content(self, target, type_name=None, data=None):
		um = None
		if data is not None:
			um = self._get_user_index_manager(target)
		if um is not None and data is not None:
			return um.index_content(data, type_name )

	def update_user_content(self, target, type_name=None, data=None):
		um = None
		if data is not None:
			um = self._get_user_index_manager(target)
		if um is not None and data is not None:
			return um.update_content(data, type_name)

	def delete_user_content(self, target, type_name=None, data=None):
		um = None
		if data is not None:
			um = self._get_user_index_manager(target)
		if um is not None and data is not None:
			return um.delete_content(data, type_name)

	@classmethod
	def onChange(cls, datasvr, msg, target=None, broadcast=None):
		handle_index_event(cls.get_shared_indexmanager(), target, msg)

	# -------------------

	def close(self):
		for bm in self.books.itervalues():
			self._close(bm)

	def _close( self, book_manager ):
		raise NotImplementedError()

