#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from zope.location import locate

import BTrees

from nti.base._compat import text_

from nti.base.interfaces import IFile

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import IPathAdapter
from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import INamedContainer
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter
from nti.contentfolder.interfaces import IContainerIdAdapter
from nti.contentfolder.interfaces import IAssociationsAdapter

from nti.zope_catalog.catalog import DeferredCatalog

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import AttributeValueIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.interfaces import IMetadataCatalog

CATALOG_NAME = 'nti.dataserver.++etc++content-resources'

#: Name index
IX_NAME = 'name'

#: Path index
IX_PATH = 'path'

#: Site index
IX_SITE = 'site'

#: Creator index
IX_CREATOR = 'creator'

#: Filename index
IX_FILENAME = 'filename'

#: MimeType index
IX_MIMETYPE = 'mimeType'

#: Content index
IX_CONTENTTYPE = 'contentType'

#: ContainerId index
IX_CONTAINERID = 'containerId'

#: Created time
IX_CREATEDTIME = 'createdTime'

#: Last time index
IX_LASTMODIFIED = 'lastModified'

#: Associations index
IX_ASSOCIATIONS = 'associations'

logger = __import__('logging').getLogger(__name__)


class MimeTypeIndex(AttributeValueIndex):
    default_field_name = 'mimeType'
    default_interface = IMimeTypeAdapter


class SiteIndex(AttributeValueIndex):
    default_field_name = 'site'
    default_interface = ISiteAdapter


class ContainerIdIndex(AttributeValueIndex):
    default_field_name = 'containerId'
    default_interface = IContainerIdAdapter


class ValidatingCreator(object):

    __slots__ = ('creator',)

    def __init__(self, obj, unused_default=None):
        if    IFile.providedBy(obj) \
           or INamedContainer.providedBy(obj):
            creator = getattr(obj, 'creator', None)
            creator = getattr(creator, 'username', creator)
            creator = getattr(creator, 'id', creator)
            if creator:
                self.creator = text_(creator.lower())

    def __reduce__(self):
        raise TypeError()


class CreatorIndex(AttributeValueIndex):
    default_field_name = 'creator'
    default_interface = ValidatingCreator


class PathIndex(AttributeValueIndex):
    default_field_name = 'path'
    default_interface = IPathAdapter


class ContentTypeIndex(AttributeValueIndex):
    default_field_name = 'contentType'
    default_interface = IFile


class FilenameIndex(AttributeValueIndex):
    default_field_name = 'filename'
    default_interface = IFilenameAdapter


class NameIndex(AttributeValueIndex):
    default_field_name = 'name'
    default_interface = INameAdapter


class ValidatingCreatedTime(object):

    __slots__ = ('createdTime',)

    def __init__(self, obj, unused_default=None):
        if    IFile.providedBy(obj) \
           or INamedContainer.providedBy(obj):
            self.createdTime = getattr(obj, 'createdTime', None)

    def __reduce__(self):
        raise TypeError()


class CreatedTimeRawIndex(RawIntegerValueIndex):
    pass


def CreatedTimeIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name='createdTime',
                                interface=ValidatingCreatedTime,
                                index=CreatedTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class ValidatingLastModified(object):

    __slots__ = ('lastModified',)

    def __init__(self, obj, unused_default=None):
        if    IFile.providedBy(obj) \
           or INamedContainer.providedBy(obj):
            self.lastModified = getattr(obj, 'lastModified', None)

    def __reduce__(self):
        raise TypeError()


class LastModififedRawIndex(RawIntegerValueIndex):
    pass


def LastModifiedIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name='lastModified',
                                interface=ValidatingLastModified,
                                index=CreatedTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class AssociationsIndex(AttributeSetIndex):
    default_field_name = 'associations'
    default_interface = IAssociationsAdapter


@interface.implementer(IMetadataCatalog)
class ContentResourcesCatalog(DeferredCatalog):

    family = BTrees.family64

    def force_index_doc(self, docid, ob):  # BWC
        self.index_doc(docid, ob)


def create_content_resources_catalog(catalog=None, family=BTrees.family64):
    if catalog is None:
        catalog = ContentResourcesCatalog(family=family)
    for name, clazz in ((IX_NAME, NameIndex),
                        (IX_PATH, PathIndex),
                        (IX_SITE, SiteIndex),
                        (IX_CREATOR, CreatorIndex),
                        (IX_FILENAME, FilenameIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_CONTAINERID, ContainerIdIndex),
                        (IX_CONTENTTYPE, ContentTypeIndex),
                        (IX_CREATEDTIME, CreatedTimeIndex),
                        (IX_LASTMODIFIED, LastModifiedIndex),
                        (IX_ASSOCIATIONS, AssociationsIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def get_content_resources_catalog(registry=component):
    return registry.queryUtility(IMetadataCatalog, name=CATALOG_NAME)
get_catalog = get_content_resources_catalog  # BWC


def install_content_resources_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_content_resources_catalog(registry=lsm)
    if catalog is not None:
        return catalog

    catalog = ContentResourcesCatalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog,
                        provided=IMetadataCatalog,
                        name=CATALOG_NAME)

    catalog = create_content_resources_catalog(catalog=catalog,
                                               family=intids.family)
    for index in catalog.values():
        intids.register(index)
    return catalog
