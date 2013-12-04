#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search index manager.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
import functools

from zope import component
from zope import interface

from perfmetrics import metric

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from . import indexagent
from . import search_query
from . import search_results
from . import interfaces as search_interfaces

def get_entity(entity):
	result = Entity.get_entity(str(entity)) \
			 if not nti_interfaces.IEntity.providedBy(entity) else entity
	return result

def entity_exists(entity):
	result = get_entity(entity)
	return result is not None

def get_user_index_manager(user, create=True):
	factory = component.getUtility(search_interfaces.IEntityIndexManagerFactory)
	user = get_entity(user)
	result = factory(user) if user and create else None
	return result

def uim_search(user, query):
	uim = get_user_index_manager(user)
	result = uim.search(query=query) if uim is not None else None
	return result

def entity_data_search(user, query, trax=True):
	transactionRunner = \
		component.getUtility(nti_interfaces.IDataserverTransactionRunner) \
		if trax else None
	func = functools.partial(uim_search, user=user, query=query)
	result = transactionRunner(func) if trax else func()
	return result

def create_content_searcher(*args, **kwargs):
	factory = component.getUtility(search_interfaces.IContentSearcherFactory)
	result = factory(*args, **kwargs)
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

	def __init__(self, parallel_search=True):
		self.parallel_search = parallel_search

	@classmethod
	def get_dfls(cls, username, sort=False):
		user = get_entity(username)
		fls = getattr(user, 'getFriendsLists', lambda s: ())(user)
		condition = nti_interfaces.IDynamicSharingTargetFriendsList.providedBy
		result = [x for x in fls if condition(x)]
		return result

	@classmethod
	def get_user_dymamic_memberships(cls, username, sort=False):
		user = get_entity(username)
		everyone = get_entity('Everyone')
		result = getattr(user, 'dynamic_memberships', ())
		result = [x for x in result if x != everyone and x is not None]
		return result

	@classmethod
	def get_search_memberships(cls, username):
		result = cls.get_user_dymamic_memberships(username) + cls.get_dfls(username)
		result = {e.username.lower():e for e in result}  #  no duplicates
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
		cnt_data = self.content_suggest_and_search(query=query)
		ugd_data = self.user_data_suggest_and_search(query=query)
		results = search_results.merge_suggest_and_search_results(cnt_data, ugd_data)
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

	def register_content(self, ntiid=None, *args, **kwargs):
		if not ntiid:
			return False
		ntiid = ntiid.lower()
		result = component.queryUtility(search_interfaces.IContentSearcher,
									 	name=ntiid) is not None
		if not result:
			searcher = create_content_searcher(ntiid=ntiid, *args, **kwargs)
			if searcher is not None:
				component.provideUtility(searcher, search_interfaces.IContentSearcher,
									 	 name=ntiid)
				result = True
				logger.info("Content '%s' has been added to index manager", ntiid)
			else:
				logger.error("Content '%s' could not be added to index manager", ntiid)
		return result

	add_book = register_content

	def get_content_searcher(self, query):
		name = query.indexid.lower() if query.indexid else u''
		searcher = component.queryUtility(search_interfaces.IContentSearcher, name=name)
		return searcher

	def content_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_search_results(query)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			r = searcher.search(query)
			results = search_results.merge_search_results(r, results) \
					  if r is not None else results
		return results

	def content_suggest_and_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_and_search_results(query)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			r = searcher.suggest_and_search(query)
			results = search_results.merge_suggest_and_search_results(r, results) \
					  if r is not None else results
		return results

	def content_suggest(self, query, *args, **kwargs):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_results(query)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			r = searcher.suggest(query)
			results = search_results.merge_suggest_results(r, results) \
					  if r is not None else results
		return results

	@classmethod
	def _get_search_entities(cls, username):
		result = [username] + cls.get_search_memberships(username)
		return result

	def _get_search_uims(self, username):
		result = []
		for name in self._get_search_entities(username):
			uim = get_user_index_manager(name)
			if uim is not None:
				result.append(uim)
		return result

	def user_data_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_search_results(query)
		entities = self._get_search_entities(query.username)
		if self.parallel_search:
			procs = [gevent.spawn(entity_data_search, username, query)
					 for username in entities]
			gevent.joinall(procs)
			for proc in procs:
				rest = proc.value
				results = search_results.merge_search_results (results, rest)
		else:
			for name in entities:
				rest = uim_search(name, query)
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
		um = get_user_index_manager(target)
		if data is not None and um is not None:
			um.index_content(data, type_name=type_name)

	def update_user_content(self, target, data, type_name=None):
		um = get_user_index_manager(target)
		if data is not None and um is not None:
			um.update_content(data, type_name=type_name)
			um = get_user_index_manager(target)

	def delete_user_content(self, target, data, type_name=None):
		um = get_user_index_manager(target)
		if data is not None and um is not None:
			um.delete_content(data, type_name=type_name)
			um = get_user_index_manager(target)

	def unindex(self, target, uid):
		um = get_user_index_manager(target)
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
