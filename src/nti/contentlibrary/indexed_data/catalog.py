#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.common._compat import integer_types

from nti.common.proxy import removeAllProxies

from nti.contentlibrary.indexed_data.interfaces import INTIIDAdapter
from nti.contentlibrary.indexed_data.interfaces import INamespaceAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainersAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainedTypeAdapter

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

from nti.zope_catalog.catalog import Catalog
from nti.zope_catalog.catalog import ResultSet

from nti.zope_catalog.index import SetIndex as RawSetIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex

CATALOG_INDEX_NAME = '++etc++contentlibrary.catalog'

IX_SITE = 'site'
IX_TYPE = 'type'
IX_NTIID = 'ntiid'
IX_NAMESPACE = 'namespace'
IX_CONTAINERS = 'containers'

def to_iterable(value):
	if isinstance(value, (list, tuple, set)):
		result = value
	else:
		result = (value,) if value is not None else ()
	result = tuple(getattr(x, '__name__', x) for x in result)
	return result

def get_uid(item, intids=None):
	if not isinstance(item, integer_types):
		item = removeAllProxies(item)
		intids = component.getUtility(IIntIds) if intids is None else intids
		result = intids.queryId(item)
	else:
		result = item
	return result
	
class RetainSetIndex(RawSetIndex):
	"""
	A set index that retains the old values.
	"""

	def to_iterable(self, value=None):
		result = to_iterable(value)
		return result

	def index_doc(self, doc_id, value):
		value = {v for v in self.to_iterable(value) if v is not None}
		old = self.documents_to_values.get(doc_id) or set()
		if value.difference(old):
			value.update(old or ())
			result = super(RetainSetIndex, self).index_doc(doc_id, value)
			return result

	def remove(self, doc_id, value):
		old = set(self.documents_to_values.get(doc_id) or ())
		if not old:
			return
		for v in to_iterable(value):
			old.discard(v)
		if old:
			super(RetainSetIndex, self).index_doc(doc_id, old)
		else:
			super(RetainSetIndex, self).unindex_doc(doc_id)

class ValidatingSiteName(object):

	__slots__ = (b'site',)

	def __init__(self, obj, default=None):
		folder = find_interface(obj, IHostPolicyFolder, strict=False)
		if folder is not None:
			self.site = folder.__name__

	def __reduce__(self):
		raise TypeError()

class SiteIndex(ValueIndex):
	default_field_name = 'site'
	default_interface = ValidatingSiteName

class TypeIndex(ValueIndex):
	default_field_name = 'type'
	default_interface = IContainedTypeAdapter
	
class NamespaceIndex(ValueIndex):
	default_field_name = 'namespace'
	default_interface = INamespaceAdapter

class NTIIDIndex(ValueIndex):
	default_field_name = 'ntiid'
	default_interface = INTIIDAdapter

class ContainersIndex(RetainSetIndex):
	default_field_name = 'containers'
	default_interface = IContainersAdapter

class LibraryCatalog(Catalog):

	@property
	def container_index(self):
		return self[IX_CONTAINERS]

	def get_containers(self, item, intids=None):
		doc_id = get_uid(item, intids)
		if doc_id is not None:
			result = self.container_index.documents_to_values.get(doc_id)
			return set(result or ())
		return set()

	def update_containers(self, item, containers=(), intids=None):
		doc_id = get_uid(item, intids)
		if doc_id is not None and containers:
			containers = to_iterable(containers)
			result = self.container_index.index_doc(doc_id, containers)
			return result
		return None

	def remove_containers(self, item, containers, intids=None):
		doc_id = get_uid(item, intids)
		if doc_id is not None:
			self.container_index.remove(doc_id, containers)
			return True
		return False

	def remove_all_containers(self, item, intids=None):
		doc_id = get_uid(item, intids)
		if doc_id is not None:
			self.container_index.unindex_doc(doc_id)
			return True
		return False

	def get_references(self,
					   ntiid=None,
					   sites=None,
					   provided=None,
					   namespace=None,
					   container_ntiids=None,
					   container_all_of=True):
		query =  {}
		container_query = 'all_of' if container_all_of else 'any_of'

		# prepare query
		for index, value, index_query in ((IX_SITE, sites, 'any_of'),
										  (IX_NTIID, ntiid, 'any_of'),
										  (IX_TYPE, provided, 'any_of'),
										  (IX_NAMESPACE, namespace, 'any_of'),
							  			  (IX_CONTAINERS, container_ntiids, container_query)):
			if value is not None:
				value = to_iterable(value)
				apply[index] = {index_query: value}
		
		# query catalog
		result = self.apply(query)
		return result if result is not None else self.family.IF.LFSet()

	def search_objects(self,
					   ntiid=None,
					   sites=None,
					   provided=None,
					   namespace=None,
					   container_ntiids=None,
					   container_all_of=True,
					   intids=None):
		intids = component.queryUtility(IIntIds) if intids is None else intids
		if intids is not None:
			refs = self.get_references(ntiid=ntiid,
									   sites=sites,
									   provided=provided,
									   namespace=namespace,
									   container_ntiids=container_ntiids,
									   container_all_of=container_all_of)
			result = ResultSet(refs, intids)
		else:
			result = ()
		return result

def install_library_catalog(site_manager_container, intids=None):
	lsm = site_manager_container.getSiteManager()
	intids = lsm.getUtility(IIntIds) if intids is None else intids
	catalog = lsm.queryUtility(ICatalog, name=CATALOG_INDEX_NAME)
	if catalog is not None:
		return catalog

	catalog = LibraryCatalog()
	catalog.__name__ = CATALOG_INDEX_NAME
	catalog.__parent__ = site_manager_container
	intids.register(catalog)
	lsm.registerUtility(catalog, provided=ICatalog, name=CATALOG_INDEX_NAME)
	
	for name, clazz in ( (IX_SITE, SiteIndex),
						 (IX_TYPE, TypeIndex),
						 (IX_NTIID, NTIIDIndex),
						 (IX_NAMESPACE, NamespaceIndex),
						 (IX_CONTAINERS, ContainersIndex),):
		index = clazz(family=intids.family)
		intids.register(index)
		locate(index, catalog, name)
		catalog[name] = index
	return catalog
