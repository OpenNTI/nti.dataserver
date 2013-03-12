# -*- coding: utf-8 -*-
"""
Search index manager.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface
from zope.event import notify

from perfmetrics import metric

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from .constants import content_
from ._search_query import QueryObject
from ._indexagent import handle_index_event
from . import interfaces as search_interfaces
from ._datastructures import CaseInsensitiveDict
from ._search_results import empty_search_results
from ._search_results import merge_search_results
from ._search_results import empty_suggest_results
from ._search_results import merge_suggest_results
from ._search_results import empty_suggest_and_search_results
from ._search_results import merge_suggest_and_search_results

@interface.implementer(search_interfaces.IIndexManager)
class IndexManager(object):

	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls, *args, **kwargs)
		return cls.indexmanager

	def __init__(self, bookidx_manager_factory, useridx_manager_adapter):
		self.books = CaseInsensitiveDict()
		self.bookidx_manager_factory = bookidx_manager_factory
		self.useridx_manager_adapter = useridx_manager_adapter

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return 'IndexManager(books=%s, %s)' % (len(self.books), self.useridx_manager_adapter)

	def get_entity(self, username):
		result = Entity.get_entity(username)
		return result

	def users_exists(self, username):
		result = self.get_entity(username)
		return result is not None

	def get_dfls(self, username, sort=False):
		user = self.get_entity(username)
		fls = getattr(user, 'getFriendsLists', lambda s: ())(user)
		result = [x for x in fls if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(x)]
		return result

	def get_user_dymamic_memberships(self, username, sort=False):
		user = self.get_entity(username)
		everyone = self.get_entity('Everyone')
		result = getattr(user, 'dynamic_memberships', ())
		result = [x for x in result if x != everyone and x is not None]
		return result

	def get_search_memberships(self, username):
		result = self.get_user_dymamic_memberships(username) + self.get_dfls(username)
		result = {e.username.lower():e for e in result}  # make sure there is no duplicate
		result = sorted(result.values(), key=lambda e: e.username.lower())
		return result

	@metric
	def search(self, query):
		query = QueryObject.create(query)
		cnt_results = self.content_search(query=query)
		ugd_results = self.user_data_search(query=query)
		results = merge_search_results(cnt_results, ugd_results)
		logger.debug("Query '%s' returned %s hit(s)" % (query.term, len(results)))
		return results

	@metric
	def suggest_and_search(self, query):
		query = QueryObject.create(query)
		cnt_results = self.content_suggest_and_search(query=query)
		ugd_results = self.user_data_suggest_and_search(query=query)
		results = merge_suggest_and_search_results(cnt_results, ugd_results)
		return results

	@metric
	def suggest(self, query):
		query = QueryObject.create(query)
		cnt_results = self.content_suggest(query=query)
		ugd_results = self.user_data_suggest(query=query)
		results = merge_suggest_results(cnt_results, ugd_results)
		return results

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

	def _valid_query(self, query):
		result = not query.is_empty
		if result:
			result = not query.searchOn or content_ in query.searchOn
		return result

	def _query_books(self, query):
		return  (query.indexid,)

	def content_search(self, query):
		query = QueryObject.create(query)
		results = empty_search_results(query)
		if self._valid_query(query):
			books = self._query_books(query)
			for book in books:
				bm = self.get_book_index_manager(book)
				r = bm.search(query) if bm is not None else None
				results = merge_search_results(r, results) if r is not None else results
		return results

	def content_suggest_and_search(self, query):
		query = QueryObject.create(query)
		results = empty_suggest_and_search_results(query)
		if self._valid_query(query):
			books = self._query_books(query)
			for book in books:
				bm = self.get_book_index_manager(book)
				r = bm.suggest_and_search(query) if bm is not None else None
				results = merge_suggest_and_search_results(r, results) if r is not None else results
		return results

	def content_suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query)
		results = empty_suggest_results(query)
		if self._valid_query(query):
			books = self._query_books(query)
			for book in books:
				bm = self.get_book_index_manager(book)
				r = bm.suggest(query) if bm is not None else None
				results = merge_suggest_results(r, results) if r is not None else results
		return results

	def _get_user_index_manager(self, target, create=True):
		if isinstance(target, six.string_types):
			target = self.get_entity(target)
		result = self.useridx_manager_adapter(target, None) if target and create else None
		return result

	def _get_search_uims(self, username):
		result = []
		for name in [username] + self.get_search_memberships(username):
			uim = self._get_user_index_manager(name)
			if uim is not None:
				result.append(uim)
		return result

	def user_data_search(self, query):
		query = QueryObject.create(query)
		results = empty_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.search(query=query)
			results = merge_search_results (results, rest)
		return results

	def user_data_suggest_and_search(self, query):
		query = QueryObject.create(query)
		results = empty_suggest_and_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest_and_search(query=query)
			results = merge_suggest_and_search_results (results, rest)
		return results

	def user_data_suggest(self, query):
		query = QueryObject.create(query)
		results = empty_suggest_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest(query=query)
			results = merge_suggest_results(results, rest)
		return results

	def index_user_content(self, target, data, type_name=None):
		um = None
		if data is not None:
			um = self._get_user_index_manager(target)
		if um is not None and data is not None and um.index_content(data, type_name=type_name):
			notify(search_interfaces.ObjectIndexedEvent(data, target))

	def update_user_content(self, target, data, type_name=None):
		um = None
		if data is not None:
			um = self._get_user_index_manager(target)
		if um is not None and data is not None and um.update_content(data, type_name=type_name):
			notify(search_interfaces.ObjectReIndexedEvent(data, target))

	def delete_user_content(self, target, data, type_name=None):
		um = None
		if data is not None:
			um = self._get_user_index_manager(target)
		if um is not None and data is not None and um.delete_content(data, type_name=type_name):
			notify(search_interfaces.ObjectUnIndexedEvent(data, target))

	@classmethod
	def onChange(cls, datasvr, msg, target=None, broadcast=None):
		handle_index_event(cls.get_shared_indexmanager(), target, msg, broadcast=broadcast)

	def close(self):
		for bm in self.books.itervalues():
			self._close(bm)

	def _close(self, bm):
		close_m = getattr(bm, 'close', None)
		if close_m is not None:
			close_m()
