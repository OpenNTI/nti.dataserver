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

from zope.deprecation import deprecated

from zope.intid import IIntIds

from zope.location import locate

from nti.coremetadata.interfaces import IRecordable

from nti.traversal.traversal import find_interface

from nti.zope_catalog.catalog import Catalog

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
IX_TYPE = 'type'
IX_LOCKED = 'locked'
IX_ATTRIBUTES = 'attributes'
IX_CREATEDTIME = 'createdTime'
IX_USERNAME = IX_PRINCIPAL = 'principal'
IX_RECORDABLE = IX_TARGET_INTID = 'targetIntId'

deprecated('SiteIndex', 'No longer used')
class SiteIndex(RawSetIndex):
	pass

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
			intids = component.queryUtility(IIntIds)  # test mode
			self.intid = intids.queryId(source) if intids is not None else None

	def __reduce__(self):
		raise TypeError()

class TargetIntIDIndex(IntegerAttributeIndex):
	field_callable = None  # XXX: Avoid migration
	field_name = default_field_name = 'intid'
	interface = default_interface = ValidatingTargetIntID

class TIDIndex(AttributeValueIndex):
	default_field_name = 'tid'
	default_interface = ITransactionRecord

class TypeIndex(AttributeValueIndex):
	default_field_name = 'type'
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
						(IX_TYPE, TypeIndex),
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

def _yield_ids(doc_ids, intids, objects=True):
	for uid in doc_ids or ():
		if intids is None:  # tests
			yield uid
		else:
			obj = intids.queryObject(uid)
			if IRecordable.providedBy(obj):
				yield obj if objects else uid

def get_locked(objects=True, catalog=None, intids=None):
	"""
	return the objects/docids in the locked index
	"""
	if catalog is None:
		catalog = component.getUtility(IMetadataCatalog, name=CATALOG_NAME)

	locked_index = catalog[IX_LOCKED]
	intids = component.queryUtility(IIntIds) if intids is None else intids
	doc_ids = catalog.family.IF.LFSet(locked_index.documents_to_values.keys())
	return _yield_ids(doc_ids, intids, objects) if objects else doc_ids

def get_targets(objects=True, catalog=None, intids=None):
	"""
	return the objects/docids in the target index
	"""
	if catalog is None:
		catalog = component.getUtility(IMetadataCatalog, name=CATALOG_NAME)

	# ids in transactions
	target_index = catalog[IX_TARGET_INTID]
	intids = component.queryUtility(IIntIds) if intids is None else intids
	doc_ids = catalog.family.IF.LFSet(target_index.values_to_documents.keys())
	return _yield_ids(doc_ids, intids, objects) if objects else doc_ids

def get_recordables(objects=True, catalog=None, intids=None):
	"""
	return the recordable objects/docids in the catalog
	"""

	if catalog is None:
		catalog = component.getUtility(IMetadataCatalog, name=CATALOG_NAME)
	intids = component.queryUtility(IIntIds) if intids is None else intids

	doc_ids = set()
	doc_ids.update(get_locked(False, catalog, intids))
	doc_ids.update(get_targets(False, catalog, intids))
	return _yield_ids(doc_ids, intids, objects) if objects else doc_ids
