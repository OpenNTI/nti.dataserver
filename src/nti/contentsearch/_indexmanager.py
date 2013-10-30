#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search index manager.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import gevent
import functools

from zope import component
from zope import interface
from zope.event import notify

from perfmetrics import metric

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.maps import CaseInsensitiveDict

from . import indexagent
from . import search_query
from . import search_results
from . import interfaces as search_interfaces

def uim_search(username, query, indexmanager=None):
	indexmanager = 	component.getUtility(search_interfaces.IIndexManager) \
					if indexmanager is None else indexmanager
	uim = indexmanager._get_user_index_manager(username)
	result = uim.search(query=query) if uim is not None else None
	return result

def entity_ugd_search(username, query, trax=True):
	transactionRunner = \
		component.getUtility(nti_interfaces.IDataserverTransactionRunner) if trax else None
	func = functools.partial(uim_search, username=username, query=query)
	result = transactionRunner(func) if trax else func()
	return result

@interface.implementer(search_interfaces.IIndexManager)
class IndexManager(object):

	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls)
		return cls.indexmanager

	def __init__(self, bookidx_manager_factory, useridx_manager_adapter,
				 parallel_search=True):
		self.books = CaseInsensitiveDict()
		self.parallel_search = parallel_search
		self.bookidx_manager_factory = bookidx_manager_factory
		self.useridx_manager_adapter = useridx_manager_adapter

	def __str__(self):
		return 'IndexManager(books=%s, %s)' % (len(self.books), self.useridx_manager_adapter)

	__repr__ = __str__

	@classmethod
	def get_entity(cls, username):
		result = Entity.get_entity(username)
		return result

	@classmethod
	def users_exists(cls, username):
		result = cls.get_entity(username)
		return result is not None

	@classmethod
	def get_dfls(cls, username, sort=False):
		user = cls.get_entity(username)
		fls = getattr(user, 'getFriendsLists', lambda s: ())(user)
		result = [x for x in fls if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(x)]
		return result

	@classmethod
	def get_user_dymamic_memberships(cls, username, sort=False):
		user = cls.get_entity(username)
		everyone = cls.get_entity('Everyone')
		result = getattr(user, 'dynamic_memberships', ())
		result = [x for x in result if x != everyone and x is not None]
		return result

	@classmethod
	def get_search_memberships(cls, username):
		result = cls.get_user_dymamic_memberships(username) + cls.get_dfls(username)
		result = {e.username.lower():e for e in result}  # make sure there is no duplicate
		result = sorted(result.values(), key=lambda e: e.username.lower())
		return result

	@metric
	def search(self, query):
		query = search_query.QueryObject.create(query)
		cnt_results = self.content_search(query=query)
		ugd_results = self.user_data_search(query=query)
		results = search_results.merge_search_results(cnt_results, ugd_results)
		logger.debug("Query '%s' returned %s hit(s)" % (query.term, len(results)))
		return results

	@metric
	def suggest_and_search(self, query):
		query = search_query.QueryObject.create(query)
		cnt_results = self.content_suggest_and_search(query=query)
		ugd_results = self.user_data_suggest_and_search(query=query)
		results = search_results.merge_suggest_and_search_results(cnt_results, ugd_results)
		return results

	@metric
	def suggest(self, query):
		query = search_query.QueryObject.create(query)
		cnt_results = self.content_suggest(query=query)
		ugd_results = self.user_data_suggest(query=query)
		results = search_results.merge_suggest_results(cnt_results, ugd_results)
		return results

	def get_book_index_manager(self, indexid):
		return self.books.get(indexid, None) if indexid is not None else None

	def add_book(self, indexname, ntiid=None, *args, **kwargs):
		result = False
		indexid = indexname if not ntiid else ntiid
		if indexid not in self.books:
			bmi = self.bookidx_manager_factory(indexname=indexname, ntiid=ntiid, **kwargs)
			if bmi is not None:
				result = True
				self.books[indexid] = bmi
				logger.info("Book index '%s,%r' has been added to index manager" % (indexname, ntiid))
			else:
				logger.warn("Could not add book index '%s,%r,%r' to index manager" % (indexname, ntiid, kwargs))
		return result

	def _query_books(self, query):
		return  (query.indexid,) if query.indexid else ()

	def content_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_search_results(query)
		books = self._query_books(query)
		for book in books:
			bm = self.get_book_index_manager(book)
			r = bm.search(query) if bm is not None else None
			results = search_results.merge_search_results(r, results) if r is not None else results
		return results

	def content_suggest_and_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_and_search_results(query)
		books = self._query_books(query)
		for book in books:
			bm = self.get_book_index_manager(book)
			r = bm.suggest_and_search(query) if bm is not None else None
			results = search_results.merge_suggest_and_search_results(r, results) if r is not None else results
		return results

	def content_suggest(self, query, *args, **kwargs):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_results(query)
		books = self._query_books(query)
		for book in books:
			bm = self.get_book_index_manager(book)
			r = bm.suggest(query) if bm is not None else None
			results = search_results.merge_suggest_results(r, results) if r is not None else results
		return results

	def _get_user_index_manager(self, target, create=True):
		if isinstance(target, six.string_types):
			target = self.get_entity(target)
		result = self.useridx_manager_adapter(target, None) if target and create else None
		return result

	@classmethod
	def _get_search_entities(cls, username):
		result = [username] + cls.get_search_memberships(username)
		return result

	def _get_search_uims(self, username):
		result = []
		for name in self._get_search_entities(username):
			uim = self._get_user_index_manager(name)
			if uim is not None:
				result.append(uim)
		return result

	def user_data_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_search_results(query)
		entities = self._get_search_entities(query.username)
		if self.parallel_search:
			procs = [gevent.spawn(entity_ugd_search, username, query) for username in entities]
			gevent.joinall(procs)
			for proc in procs:
				rest = proc.value
				results = search_results.merge_search_results (results, rest)
		else:
			for name in entities:
				rest = uim_search(name, query, self)
				results = search_results.merge_search_results (results, rest)
		return results

	def user_data_suggest_and_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_and_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest_and_search(query=query)
			results = search_results.merge_suggest_and_search_results (results, rest)
		return results

	def user_data_suggest(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest(query=query)
			results = search_results.merge_suggest_results(results, rest)
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

	def unindex(self, target, uid):
		um = self._get_user_index_manager(target)
		if um is not None:
			return um.unindex(uid)
		return False

	def close(self):
		for bm in self.books.itervalues():
			self._close(bm)

	def _close(self, bm):
		close_m = getattr(bm, 'close', None)
		if close_m is not None:
			close_m()

	@classmethod
	def onChange(cls, datasvr, msg, target=None, broadcast=None):
		indexagent.handle_index_event(cls.get_shared_indexmanager(), target, msg,
									  broadcast=broadcast)
