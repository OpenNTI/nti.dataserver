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

from nti.common.property import Lazy

from nti.coremetadata.interfaces import IRecordable

from nti.traversal.traversal import find_interface

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.interfaces import IMetadataCatalog

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.string import StringTokenNormalizer
from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from .interfaces import ITransactionRecord

CATALOG_NAME = 'nti.dataserver.++etc++recorder-catalog'

IX_TID = 'tid'
IX_ATTRIBUTES = 'attributes'
IX_CREATEDTIME = 'createdTime'
IX_TARGET_INTID = 'targetIntId'
IX_USERNAME = IX_PRINCIPAL = 'principal'

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
			self.intid = self.intid.queryId(source) if source is not None else None

	@Lazy
	def intid(self):
		return component.getUtility(IIntIds)

	def __reduce__(self):
		raise TypeError()

class TargetIntIDIndex(RawIntegerValueIndex):
	default_field_name = 'intid'
	default_interface = ValidatingTargetIntID

class TIDIndex(ValueIndex):
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

@interface.implementer(IMetadataCatalog)
class MetadataRecorderCatalog(Catalog):

	super_index_doc = Catalog.index_doc

	def index_doc(self, docid, ob):
		pass

	def force_index_doc(self, docid, ob):
		self.super_index_doc(docid, ob)

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

	for name, clazz in ((IX_TID, TIDIndex),
						(IX_PRINCIPAL, PrincipalIndex),
						(IX_CREATEDTIME, CreatedTimeIndex),
						(IX_ATTRIBUTES, AttributeSetIndex),
						(IX_TARGET_INTID, TargetIntIDIndex)):
		index = clazz(family=intids.family)
		intids.register(index)
		locate(index, catalog, name)
		catalog[name] = index
	return catalog
