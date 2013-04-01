# -*- coding: utf-8 -*-
"""
Whoosh user search adapter.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hashlib import md5

try:
	from gevent.lock import RLock
except ImportError:
	from threading import RLock

from zope import interface
from zope import component
from zope.proxy import ProxyBase
from zope.annotation import factory as an_factory

from nti.dataserver import interfaces as nti_interfaces

from .common import get_type_name
from ._datastructures import LFUMap
from .common import sort_search_types
from ._search_query import QueryObject
from . import _search_results as srlts
from . import interfaces as search_interfaces
from .constants import ugd_indexable_type_names
from .common import normalize_type_name as _ntm
from ._whoosh_index import get_indexable_object
from ._whoosh_indexstorage import get_index_writer
from ._search_indexmanager import _SearchEntityIndexManager

def get_indexname(username, type_name, use_md5=True):
	type_name = _ntm(type_name)
	if use_md5:
		m = md5()
		m.update(username)
		m.update(type_name)
		indexname = str(m.hexdigest())
	else:
		indexname = "%s_%s" % (username, type_name)
	return indexname

# proxy class to wrap an whoosh index

class _NoLockingProxy(ProxyBase):

	def __enter__(self):
		pass

	def __exit__(self, *args, **kwargs):
		pass

class _Proxy(ProxyBase):

	def __init__(self, obj):
		super(_Proxy, self).__init__(obj)
		self.rlock = RLock()

	def __enter__(self):
		return self.rlock.__enter__()

	def __exit__(self, *args, **kwargs):
		return self.rlock.__exit__(*args, **kwargs)

# lease frequently used map to keep open indices

def _safe_index_close(index):
	with index:
		try:
			index.close()
		except Exception:
			pass

# entity adapter for whoosh indicies

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(search_interfaces.IWhooshEntityIndexManager)
class _BaseWhooshEntityIndexManager(_SearchEntityIndexManager):

	delay = 0.25
	maxiters = 40
	use_md5 = False

	@property
	def writer_ctor_args(self):
		return self.storage.ctor_args()

	@property
	def writer_commit_args(self):
		return self.storage.commit_args()

	# -------------------

	def _register_index(self, type_name, index_name, index):
		self[type_name] = index_name
		return _Proxy(index)

	def _get_indexname(self, type_name):
		indexname = get_indexname(self.username, type_name, self.use_md5)
		return indexname

	def _get_index_writer(self, index):
		return get_index_writer(index, self.writer_ctor_args, self.maxiters, self.delay)

	# -------------------

	def _adapt_search_on_types(self, searchOn=None):
		indexables = ugd_indexable_type_names
		searchOn = [_ntm(x) for x in searchOn if _ntm(x) in indexables] if searchOn else indexables
		result = sort_search_types(searchOn)
		return result

	def _do_search(self, query, is_ngram_search=False, **kwargs):
		query = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_search_on_types(query.searchOn)
		results = srlts.empty_search_results(query)
		for type_name in searchOn:
			index = self._get_or_create_index(type_name)
			with index:
				indexable = self.get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.search(searcher, query)
					results = srlts.merge_search_results(results, rs)
		return results

	def search(self, query, *args, **kwargs):
		results = self._do_search(query, False, **kwargs)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_search_on_types(query.searchOn)
		results = srlts.empty_suggest_and_search_results(query)
		for type_name in searchOn:
			index = self._get_or_create_index(type_name)
			with index:
				indexable = self.get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest_and_search(searcher, query)
					results = srlts.merge_suggest_and_search_results(results, rs)
		return results

	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_search_on_types(query.searchOn)
		results = srlts.empty_suggest_results(query)
		for type_name in searchOn:
			index = self._get_or_create_index(type_name)
			with index:
				indexable = self.get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest(searcher, query)
					results = srlts.merge_suggest_results(results, rs)
		return results

	# -------------------

	def _get_type_name(self, data=None, **kwargs):
		type_name = kwargs.get('type_name', None) or kwargs.get('typeName', None)
		if not type_name:
			type_name = get_type_name(data) if data else None
		return _ntm(type_name)

	def _index_content(self, indexable, writer, data):
		result = indexable.index_content(writer, data, **self.writer_commit_args)
		if not result:
			writer.cancel()
		return result

	def index_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				indexable = self.get_indexable_object(type_name)
				writer = self._get_index_writer(index)
				return self._index_content(indexable, writer, data)
		return False

	def _update_content(self, indexable, writer, data):
		result = indexable.update_content(writer, data, **self.writer_commit_args)
		if not result:
			writer.cancel()
		return result

	def update_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				indexable = self.get_indexable_object(type_name)
				writer = self._get_index_writer(index)
				return self._update_content(indexable, writer, data)
		return False

	def _delete_content(self, indexable, writer, data):
		result = indexable.delete_content(writer, data, **self.writer_commit_args)
		if not result:
			writer.cancel()
		return result

	def delete_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				indexable = self.get_indexable_object(type_name)
				writer = self._get_index_writer(index)
				return self._delete_content(indexable, writer, data)
		return False

	def remove_index(self, type_name, *args, **kwargs):
		type_name = _ntm(type_name)
		return self.pop(type_name, None)

	def get_indexable_object(self, type_name):
		indexable = get_indexable_object(type_name)
		if not hasattr(indexable, 'get_object'):
			setattr(indexable , 'get_object', self.get_object)
		return indexable

def _on_index_removed(key, value):
	_safe_index_close(value)

class _WhooshEntityIndexManager(_BaseWhooshEntityIndexManager):

	use_md5 = True
	whoosh_indices = LFUMap(maxsize=500, on_removal_callback=_on_index_removed)

	@property
	def storage(self):
		result = component.getUtility(search_interfaces.IWhooshIndexStorage)
		return result

	def _register_index(self, type_name, index_name, index):
		index = super(_WhooshEntityIndexManager, self)._register_index(type_name, index_name, index)
		self.whoosh_indices[index_name] = index
		return index

	def _get_or_create_index(self, type_name):
		type_name = _ntm(type_name)
		indexname = self._get_indexname(type_name)
		index = self.whoosh_indices.get(indexname, None)
		if not index:
			indexable = self.get_indexable_object(type_name)
			schema = indexable.schema if indexable else None
			if schema:
				index = self.storage.get_or_create_index(indexname=indexname,
														 schema=schema,
														 username=self.username)
				index = self._register_index(type_name, indexname, index)
		return index

	def remove_index(self, type_name, *args, **kwargs):
		type_name = _ntm(type_name)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				self.pop(type_name, None)
				self.whoosh_indices.pop(type_name, None)
				_safe_index_close(index)

_WhooshEntityIndexManagerFactory = an_factory(_WhooshEntityIndexManager)
