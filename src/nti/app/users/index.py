#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import BTrees

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.coremetadata.interfaces import IContextLastSeenRecord

from nti.zope_catalog.catalog import DeferredCatalog

from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.interfaces import IDeferredCatalog

#: The name of the utility that the Zope Catalog
#: should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++contextlastseen-catalog'

IX_CONTEXT = 'context'
IX_USERNAME = 'username'
IX_TIMESTAMP = 'timestamp'

logger = __import__('logging').getLogger(__name__)


class UsernameIndex(ValueIndex):
    default_field_name = IX_USERNAME
    default_interface = IContextLastSeenRecord


class ContextIndex(ValueIndex):
    default_field_name = IX_CONTEXT
    default_interface = IContextLastSeenRecord


class TimeStampRawIndex(RawIntegerValueIndex):
    pass


def TimeStampIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name=IX_TIMESTAMP,
                                interface=IContextLastSeenRecord,
                                index=TimeStampRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


@interface.implementer(IDeferredCatalog)
class ContextLastSeenCatalog(DeferredCatalog):
    family = BTrees.family64


def get_context_lastseen_catalog(registry=component):
    catalog = registry.queryUtility(IDeferredCatalog, name=CATALOG_NAME)
    return catalog


def create_context_lastseen_catalog(catalog=None, family=BTrees.family64):
    if catalog is None:
        catalog = ContextLastSeenCatalog(family)

    for name, clazz in ((IX_CONTEXT, ContextIndex),
                        (IX_USERNAME, UsernameIndex),
                        (IX_TIMESTAMP, TimeStampIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index

    return catalog


def install_context_lastseen_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_context_lastseen_catalog(lsm)
    if catalog is not None:
        return catalog

    catalog = create_context_lastseen_catalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog,
                        provided=IDeferredCatalog,
                        name=CATALOG_NAME)

    for index in catalog.values():
        intids.register(index)
    return catalog
