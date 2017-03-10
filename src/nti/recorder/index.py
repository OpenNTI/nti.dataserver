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

from zope.intid.interfaces import IIntIds

from zope.location import locate

from zope.mimetype.interfaces import IContentTypeAware

from nti.coremetadata.interfaces import IRecordable
from nti.coremetadata.interfaces import IRecordableContainer

from nti.recorder.interfaces import ITransactionRecord

from nti.traversal.traversal import find_interface

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import AttributeValueIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import IntegerAttributeIndex
from nti.zope_catalog.index import SetIndex as RawSetIndex
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.interfaces import IMetadataCatalog

from nti.zope_catalog.string import StringTokenNormalizer

CATALOG_NAME = 'nti.dataserver.++etc++recorder-catalog'

#: Transaction ID index
IX_TID = 'tid'

#: Transaction type index
IX_TYPE = 'type'

#: Recordable object locked attribute index
IX_LOCKED = 'locked'

#: Recordable container object child-order-locked attribute index
IX_CHILD_ORDER_LOCKED = 'childOrderLocked'

#: Recordable object MimeType
IX_MIMETYPE = 'mimeType'

#: Transaction attribute
IX_ATTRIBUTES = 'attributes'

#: Transaction time
IX_CREATEDTIME = 'createdTime'

#: Transaction principal
IX_USERNAME = IX_PRINCIPAL = 'principal'


deprecated('SiteIndex', 'No longer used')
class SiteIndex(RawSetIndex):
    pass


class ValidatingRecordableIntID(object):

    __slots__ = (b'intid',)

    def __init__(self, obj, default=None):
        if ITransactionRecord.providedBy(obj):
            source = find_interface(obj, IRecordable, strict=False)
            intids = component.queryUtility(IIntIds)  # test mode
            if intids is not None and source is not None:
                self.intid = intids.queryId(source)

    def __reduce__(self):
        raise TypeError()


deprecated('TargetIntIDIndex', 'No longer used')
class TargetIntIDIndex(IntegerAttributeIndex):
    pass


class ValidatingMimeType(object):

    __slots__ = (b'mimeType',)

    def __init__(self, obj, default=None):
        if ITransactionRecord.providedBy(obj):
            source = find_interface(obj, IRecordable, strict=False)
        elif IRecordable.providedBy(obj):
            source = obj
        else:
            source = None
        if source is not None:
            source = IContentTypeAware(source, source)
            self.mimeType = getattr(source, 'mimeType', None) \
                         or getattr(source, 'mime_type', None)

    def __reduce__(self):
        raise TypeError()


class MimeTypeIndex(AttributeValueIndex):
    default_field_name = 'mimeType'
    default_interface = ValidatingMimeType


class PrincipalRawIndex(RawValueIndex):
    pass


def PrincipalIndex(family=None):
    return NormalizationWrapper(field_name='principal',
                                interface=ITransactionRecord,
                                index=PrincipalRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


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
            self.locked = source.isLocked()

    def __reduce__(self):
        raise TypeError()


class LockedIndex(AttributeValueIndex):
    field_name = default_field_name = 'locked'
    interface = default_interface = ValidatingLocked


class ValidatingChildOrderLocked(object):

    __slots__ = (b'child_order_locked',)

    def __init__(self, obj, default=None):
        if ITransactionRecord.providedBy(obj):
            source = find_interface(obj, IRecordableContainer, strict=False)
        elif IRecordableContainer.providedBy(obj):
            source = obj
        else:
            source = None
        if source is not None:
            self.child_order_locked = source.isChildOrderLocked()

    def __reduce__(self):
        raise TypeError()


class ChildOrderLockedIndex(AttributeValueIndex):
    field_name = default_field_name = 'child_order_locked'
    interface = default_interface = ValidatingChildOrderLocked


@interface.implementer(IMetadataCatalog)
class MetadataRecorderCatalog(Catalog):

    super_index_doc = Catalog.index_doc

    def index_doc(self, docid, ob):
        pass

    def force_index_doc(self, docid, ob):
        self.super_index_doc(docid, ob)


def create_recorder_catalog(catalog=None, family=None):
    if catalog is None:
        catalog = MetadataRecorderCatalog(family=family)
    for name, clazz in ((IX_TID, TIDIndex),
                        (IX_TYPE, TypeIndex),
                        (IX_LOCKED, LockedIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_PRINCIPAL, PrincipalIndex),
                        (IX_ATTRIBUTES, AttributeSetIndex),
                        (IX_CREATEDTIME, CreatedTimeIndex),
                        (IX_CHILD_ORDER_LOCKED, ChildOrderLockedIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def get_catalog(registry=component):
    catalog = registry.queryUtility(IMetadataCatalog, name=CATALOG_NAME)
    return catalog


def install_recorder_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_catalog(registry=lsm)
    if catalog is not None:
        return catalog

    catalog = MetadataRecorderCatalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog, 
                        provided=IMetadataCatalog, 
                        name=CATALOG_NAME)

    catalog = create_recorder_catalog(catalog=catalog, family=intids.family)
    for index in catalog.values():
        intids.register(index)
    return catalog


def get_objects(index=IX_LOCKED, provided=IRecordable, catalog=None, intids=None):
    catalog = get_catalog() if catalog is None else catalog
    pivot_index = catalog[index]
    intids = component.queryUtility(IIntIds) if intids is None else intids
    for uid in set(pivot_index.documents_to_values.keys()):
        if intids is None:  # tests
            yield uid
        else:
            obj = intids.queryObject(uid)
            if provided.providedBy(obj):
                yield obj


def get_transactions(catalog=None, intids=None, **kwargs):
    """
    return the transaction records in the catalog
    """
    return get_objects(IX_TID, ITransactionRecord, catalog, intids)


def get_recordables(catalog=None, intids=None, **kwargs):
    """
    return the recordable objects in the catalog
    """
    return get_objects(IX_LOCKED, IRecordable, catalog, intids)
