#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.intid import IIntIds

from zope.location import locate

from nti.coremetadata.interfaces import IRecordable

from nti.site.site import get_component_hierarchy_names

from nti.traversal.traversal import find_interface

from nti.zope_catalog.catalog import Catalog
from nti.zope_catalog.catalog import ResultSet

from nti.zope_catalog.interfaces import IMetadataCatalog

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import AttributeValueIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import IntegerAttributeIndex
from nti.zope_catalog.index import SetIndex as RawSetIndex
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.string import StringTokenNormalizer
from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from .interfaces import ITransactionRecord

CATALOG_NAME = 'nti.dataserver.++etc++recorder-catalog'

IX_TID = 'tid'
IX_SITE = 'site'
IX_LOCKED = 'locked'
IX_ATTRIBUTES = 'attributes'
IX_CREATEDTIME = 'createdTime'
IX_USERNAME = IX_PRINCIPAL = 'principal'
IX_RECORDABLE = IX_TARGET_INTID = 'targetIntId'

class KeepSetIndex(RawSetIndex):

	empty_set = set()

	def to_iterable(self, value):
		return value

	def index_doc(self, doc_id, value):
		value = {v for v in self.to_iterable(value) if v is not None}
		old = self.documents_to_values.get(doc_id) or self.empty_set
		if value.difference(old):
			value.update(old or ())
			result = super(KeepSetIndex, self).index_doc(doc_id, value)
			return result

	def remove(self, doc_id, value):
		old = set(self.documents_to_values.get(doc_id) or ())
		if not old:
			return
		for v in self.to_iterable(value):
			old.discard(v)
		if old:
			super(KeepSetIndex, self).index_doc(doc_id, old)
		else:
			super(KeepSetIndex, self).unindex_doc(doc_id)

class SiteIndex(KeepSetIndex):

	def to_iterable(self, value):
		if ITransactionRecord.providedBy(value):
			result = get_component_hierarchy_names()
		else:
			result = ()
		return result

class PrincipalRawIndex(RawValueIndex):
	pass

def PrincipalIndex(family=None):
	return NormalizationWrapper(field_name='principal',
								interface=ITransactionRecord,
								index=PrincipalRawIndex(family=family),
								normalizer=StringTokenNormalizer())

class ValidatingTargetIntID(object):

	__slots__ = (b'intid',)

	def __init__(self, obj, default=None):
		if ITransactionRecord.providedBy(obj):
			source = find_interface(obj, IRecordable, strict=False)
		elif IRecordable.providedBy(obj):
			source = obj
		else:
			source = None
		if source is not None:
			intids = component.queryUtility(IIntIds) # test mode
			self.intid = intids.queryId(source) if intids is not None else None

	def __reduce__(self):
		raise TypeError()

class TargetIntIDIndex(IntegerAttributeIndex):
	field_callable = None
	field_name = default_field_name = 'intid'
	interface = default_interface = ValidatingTargetIntID

class TIDIndex(AttributeValueIndex):
	default_field_name = 'tid'
	default_interface = ITransactionRecord

class CreatedTimeRawIndex(RawIntegerValueIndex):
	pass

def CreatedTimeIndex(family=None):
	return NormalizationWrapper(field_name='createdTime',
								interface=ITransactionRecord,
								index=CreatedTimeRawIndex(family=family),
								normalizer=TimestampToNormalized64BitIntNormalizer())

class AttributeSetIndex(AttributeSetIndex):
	default_field_name = 'attributes'
	default_interface = ITransactionRecord

class ValidatingLocked(object):

	__slots__ = (b'locked',)

	def __init__(self, obj, default=None):
		if ITransactionRecord.providedBy(obj):
			source = find_interface(obj, IRecordable, strict=False)
		elif IRecordable.providedBy(obj):
			source = obj
		else:
			source = None
		if source is not None:
			self.locked = source.locked

	def __reduce__(self):
		raise TypeError()

class LockedIndex(AttributeValueIndex):
	field_name = default_field_name = 'locked'
	interface = default_interface = ValidatingLocked

@interface.implementer(IMetadataCatalog)
class MetadataRecorderCatalog(Catalog):

	super_index_doc = Catalog.index_doc

	def index_doc(self, docid, ob):
		pass

	def force_index_doc(self, docid, ob):
		self.super_index_doc(docid, ob)

def create_recorder_catalog(catalog=None, family=None):
	catalog = MetadataRecorderCatalog(family=family) if catalog is None else catalog
	for name, clazz in ((IX_TID, TIDIndex),
						(IX_SITE, SiteIndex),
						(IX_LOCKED, LockedIndex),
						(IX_PRINCIPAL, PrincipalIndex),
						(IX_CREATEDTIME, CreatedTimeIndex),
						(IX_ATTRIBUTES, AttributeSetIndex),
						(IX_TARGET_INTID, TargetIntIDIndex)):
		index = clazz(family=family)
		locate(index, catalog, name)
		catalog[name] = index
	return catalog

def install_recorder_catalog(site_manager_container, intids=None):
	lsm = site_manager_container.getSiteManager()
	if intids is None:
		intids = lsm.getUtility(IIntIds)

	catalog = lsm.queryUtility(IMetadataCatalog, name=CATALOG_NAME)
	if catalog is not None:
		return catalog

	catalog = MetadataRecorderCatalog(family=intids.family)
	locate(catalog, site_manager_container, CATALOG_NAME)
	intids.register(catalog)
	lsm.registerUtility(catalog, provided=IMetadataCatalog, name=CATALOG_NAME)
	
	catalog = create_recorder_catalog(catalog=catalog)
	for index in catalog.values():
		intids.register(index)
	return catalog

def get_recordables(objects=True, catalog=None, intids=None):
	"""
	return the the recordables in the catalog
	"""
	if catalog is None:
		catalog = component.getUtility(IMetadataCatalog, name=CATALOG_NAME)

	# ids in transactions
	target_index = catalog[IX_TARGET_INTID]
	recordable_ids = catalog.family.IF.LFSet(target_index.values_to_documents.keys())
	
	# locked status
	locked_index = catalog[IX_LOCKED]
	locked_ids = catalog.family.IF.LFSet(locked_index.documents_to_values.keys())
	
	uids = catalog.family.IF.union(locked_ids, recordable_ids)
	if objects:
		intids = component.getUtility(IIntIds) if intids is None else intids
		result = ResultSet(uids, intids)
	else:
		result = uids
	return result
