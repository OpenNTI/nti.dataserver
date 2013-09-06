# -*- coding: utf-8 -*-
"""
Cloudsearch user search adapter.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys

from zope import interface
from zope import component
from zope.annotation import factory as an_factory

from perfmetrics import metricmethod

from nti.dataserver import interfaces as nti_interfaces

from ._search_results import IndexHit
from ._search_query import QueryObject
from ._cloudsearch_query import parse_query
from ._search_results import empty_search_results
from ._search_results import empty_suggest_results
from ._cloudsearch_index import search_stored_fields
from ._search_indexmanager import _SearchEntityIndexManager
from ._search_results import empty_suggest_and_search_results
from . import _cloudsearch_interfaces as cloudsearch_interfaces

from .constants import (username_, content_, intid_, type_)

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(cloudsearch_interfaces.ICloudSearchEntityIndexManager)
class _CloudSearchEntityIndexManager(_SearchEntityIndexManager):

	_v_store = None

	def _get_cs_store(self):
		if self._v_store is None:
			self._v_store = component.getUtility(cloudsearch_interfaces.ICloudSearchStore)
		return self._v_store

	def _get_search_hit(self, obj):
		cloud_data = obj['data']
		uid = cloud_data.get(intid_, None)
		uid = uid[0] if isinstance(uid, (list, tuple)) else uid
		result = self.get_object(uid) if uid is not None else None
		return IndexHit(int(uid), 1.0) if result is not None else None

	def _do_search(self, qo, creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		if qo.is_empty:
			return results

		service = self._get_cs_store()

		# perform cloud query
		start = qo.get('start', 0)
		limit = sys.maxint  # return all hits
		bq = parse_query(qo, self.username)
		objects = service.search(bq=bq, return_fields=search_stored_fields, size=limit, start=start)

		# get ds objects
		for obj in objects:
			index_hit = self._get_search_hit(obj)
			if index_hit is not None:
				results.add(index_hit)
		return results

	@metricmethod
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		results = self._do_search(qo)
		return results

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		return empty_suggest_results(qo)

	def suggest_and_search(self, query, *args, **kwargs):
		# word suggest does not seem to be supported yet in cloud search
		qo = QueryObject.create(query, **kwargs)
		return self._do_search(content_, qo, creator_method=empty_suggest_and_search_results)

	def index_content(self, data, type_name=None):
		service = self._get_cs_store()
		docid = self.get_uid(data)
		result = service.add(docid, self.username)
		service.handle_cs_errors(result, throw=True)
		return True

	# update is simply and add w/ a different version number
	update_content = index_content

	def delete_content(self, data, type_name=None):
		service = self._get_cs_store()
		docid = self.get_uid(data)
		result = service.delete(docid, self.username)
		service.handle_cs_errors(result, throw=True)
		return True

	def unindex(self, uid):
		service = self._get_cs_store()
		result = service.delete(uid, self.username)
		service.handle_cs_errors(result, throw=True)
		return True

	def get_aws_oids(self, type_name=None, size=sys.maxint):
		"""
		return a generator w/ ids of the objects indexed in aws
		"""
		# TODO: get this query through query parser
		bq = ['(and']
		bq.append("%s:'%s'" % (username_, self.username))
		if type_name:
			bq.append("%s:'%s'" % (type_, type_name))
		bq.append(')')
		bq = ' '.join(bq)

		service = self._get_cs_store()
		results = service.search(bq=bq, return_fields=[intid_], size=size, start=0)
		for r in results:
			yield r[intid_]

_CloudSearchEntityIndexManagerFactory = an_factory(_CloudSearchEntityIndexManager)
