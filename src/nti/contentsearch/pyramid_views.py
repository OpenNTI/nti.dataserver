#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface
from zope.event import notify
from zope.location import locate

from nti.dataserver.users import Entity

from . import search_utils
from . import interfaces as search_interfaces

class BaseView(object):

	name = None

	def __init__(self, request):
		self.request = request

	@property
	def query(self):
		return search_utils.create_queryobject(self.request)

	@property
	def indexmanager(self):
		return self.request.registry.getUtility(search_interfaces.IIndexManager)

	def _locate(self, obj, parent):
		# TODO: (Instead of modification info, we should be using etags here, anyway).
		locate(obj, parent, self.name)
		# TODO: Make cachable?
		from nti.appserver import interfaces as app_interfaces  # Avoid circular imports
		interface.alsoProvides(obj, app_interfaces.IUncacheableInResponse)
		return obj

	def search(self, query):
		now = time.time()
		result = self.indexmanager.search(query=query)
		metadata = result.metadata
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(search_interfaces.SearchCompletedEvent(entity, query, metadata, elapsed))
		return result

	def __call__(self):
		query = self.query
		result = self.search(query=query)
		result = self._locate(result, self.request.root)
		return result

class SearchView(BaseView):
	name = 'Search'
Search = SearchView  # BWC

class UserDataSearchView(BaseView):
	name = 'UserSearch'
UserSearch = UserDataSearchView  # BWC
