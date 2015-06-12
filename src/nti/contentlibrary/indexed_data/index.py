#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.intid import IIntIds

import BTrees

from persistent import Persistent

from nti.common.iterables import is_nonstr_iter

from nti.zope_catalog.catalog import ResultSet

from nti.zope_catalog.index import SetIndex as RawSetIndex
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex

from .interfaces import IContainedTypeAdapter
from .interfaces import IContainedObjectCatalog

from . import CATALOG_INDEX_NAME

def to_iterable(value):
	value = getattr(value, '__name__', value)
	if is_nonstr_iter(value):
		result = value
	else:
		result = (value,)
	return result

class KeepSetIndex(RawSetIndex):
	"""
	Maps object -> containedContainers. A set index that keeps the old values.
	"""

	empty_set = set()

	def index_doc(self, doc_id, value):
		value = {v for v in to_iterable(value) if v is not None}
		old = self.documents_to_values.get(doc_id) or self.empty_set
		if value.difference(old):
			value.update(old or ())
			result = super(KeepSetIndex, self).index_doc(doc_id, value)
			return result

	def remove(self, doc_id, value):
		if self.default_interface is not None:
			obj = self.default_interface(value, None)
			if obj is None:
				return None

		old = set(self.documents_to_values.get(doc_id) or ())
		if not old:
			return
		for v in to_iterable(value):
			old.discard(v)
		if old:
			super(KeepSetIndex, self).index_doc(doc_id, old)
		else:
			super(KeepSetIndex, self).unindex_doc(doc_id)

class CheckRawValueIndex(RawValueIndex):

	def index_doc(self, doc_id, value):
		if value is None:
			self.unindex_doc(doc_id)
		else:
			documents_to_values = self.documents_to_values
			old = documents_to_values.get(doc_id)
			if old is None or old != value:
				super(CheckRawValueIndex, self).index_doc(doc_id, value)

class TypeIndex(ValueIndex):
	default_field_name = 'type'
	default_interface = IContainedTypeAdapter

class NamespaceIndex(CheckRawValueIndex):
	pass

class ContainedObjectCatalog(Persistent):

	family = BTrees.family64

	def __init__(self):
		self.reset()

	def reset(self):
		# Track the object type (interface name)
		self._type_index = TypeIndex(family=self.family)
		# Track the containers the object belongs to
		self._container_index = KeepSetIndex(family=self.family)
		# Track the source/file name an object was read from
		self._namespace_index = NamespaceIndex(family=self.family)

	def _doc_id(self, item, intids=None):
		intids = component.queryUtility(IIntIds) if intids is None else intids
		if not isinstance(item, int):
			doc_id = intids.queryId(item) if intids is not None else None
		else:
			doc_id = item
		return doc_id

	def get_containers(self, item, intids=None):
		intids = component.queryUtility(IIntIds) if intids is None else intids
		doc_id = self._doc_id(item, intids)
		if doc_id is None:
			result = ()
		else:
			result = self._container_index.documents_to_values.get(doc_id)
			result = set(result or ())
		return result

	def remove_containers(self, item, containers, intids=None):
		doc_id = self._doc_id(item, intids)
		if doc_id is not None:
			self._container_index.remove(doc_id, containers)
			return True
		return False
	remove_container = remove_containers

	def remove_all_containers(self, item, intids=None):
		doc_id = self._doc_id(item, intids)
		if doc_id is not None:
			self._container_index.unindex_doc(doc_id)
			return True
		return False

	def get_references(self, container_ntiids=None, provided=None, namespace=None):
		result = None
		# Provided is interface that maps to our type adapter
		for index, value, query in ((self._type_index, provided, 'any_of'),
									(self._namespace_index, namespace, 'any_of'),
							  		(self._container_index, container_ntiids, 'all_of')):
			if value is not None:
				value = to_iterable(value)
				ids = index.apply({query: value}) or self.family.IF.LFSet()
				if result is None:
					result = ids
				else:
					result = self.family.IF.intersection(result, ids)
		return result or ()

	def search_objects(self, container_ntiids=None, provided=None, namespace=None, intids=None):
		intids = component.queryUtility(IIntIds) if intids is None else intids
		if intids is not None:
			refs = self.get_references(container_ntiids, provided, namespace)
			result = ResultSet(refs, intids)
		else:
			result = ()
		return result

	def index(self, item, container_ntiids=None, namespace=None, intids=None):
		doc_id = self._doc_id(item, intids)
		if doc_id is None:
			return False

		if namespace is not None:
			namespace = getattr(namespace, '__name__', namespace)

		for index, value in ((self._type_index, item),
							 (self._namespace_index, namespace),
							 (self._container_index, container_ntiids)):
			if value is not None:
				index.index_doc(doc_id, value)
		return True

	def unindex(self, item, intids=None):
		doc_id = self._doc_id(item, intids)
		if doc_id is None:
			return False
		for index in (self._container_index, self._type_index, self._namespace_index):
			index.unindex_doc(doc_id)
		return True

def install_container_catalog(site_manager_container, intids=None):
	lsm = site_manager_container.getSiteManager()
	if intids is None:
		intids = lsm.getUtility(IIntIds)

	catalog = ContainedObjectCatalog()
	catalog.__name__ = CATALOG_INDEX_NAME
	catalog.__parent__ = site_manager_container
	intids.register(catalog)
	lsm.registerUtility(catalog, provided=IContainedObjectCatalog, name=CATALOG_INDEX_NAME)
	return catalog
