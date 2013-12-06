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

from . import search_query
from . import search_results
from . import interfaces as search_interfaces

def get_entity(entity):
	result = Entity.get_entity(str(entity)) \
			 if not nti_interfaces.IEntity.providedBy(entity) else entity
	return result

def uim_search(user, query):
	user = get_entity(user)
	uim = search_interfaces.IRepozeEntityIndexManager(user, None)
	result = uim.search(query=query) if uim is not None else None
	return result

def entity_data_search(user, query, trax=True):
	transactionRunner = \
			component.getUtility(nti_interfaces.IDataserverTransactionRunner) \
			if trax else None
	func = functools.partial(uim_search, user=user, query=query)
	result = transactionRunner(func) if trax else func()
	return result

@interface.implementer(search_interfaces.IEntityIndexController)
class _RepozeEntityIndexController(object):

	def __init__(self, entity, parallel_search=True):
		self.entity = entity
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

	@classmethod
	def _get_search_entities(cls, username):
		result = [username] + cls.get_search_memberships(username)
		return result

	def _get_search_uims(self, username):
		result = []
		for name in self._get_search_entities(username):
			entity = get_entity(name)
			uim = search_interfaces.IRepozeEntityIndexManager(entity, None)
			if uim is not None:
				result.append(uim)
		return result

	@metric
	def search(self, query):
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

	@metric
	def suggest_and_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_and_search_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest_and_search(query=query)
			results = search_results.merge_suggest_and_search_results (results, rest)
		return results

	@metric
	def suggest(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_results(query)
		for uim in self._get_search_uims(query.username):
			rest = uim.suggest(query=query)
			results = search_results.merge_suggest_results(results, rest)
		return results

	def index_content(self, data):
		um = search_interfaces.IRepozeEntityIndexManager(self.entity, None)
		if data is not None and um is not None:
			um.index_content(data)

	def update_content(self, data):
		um = search_interfaces.IRepozeEntityIndexManager(self.entity, None)
		if data is not None and um is not None:
			um.update_content(data)

	def delete_content(self, data):
		um = search_interfaces.IRepozeEntityIndexManager(self.entity, None)
		if data is not None and um is not None:
			um.delete_content(data)

	def unindex(self, uid):
		um = search_interfaces.IRepozeEntityIndexManager(self.entity, None)
		if um is not None:
			return um.unindex(uid)
		return False
