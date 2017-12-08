#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from zope.location import locate

import BTrees

from nti.dataserver.interfaces import IUser

from nti.identifiers.interfaces import IExternalIdentifierUtility

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.index import AttributeSetIndex

CATALOG_NAME = 'nti.dataserver.++etc++external-identifier-catalog'

#: External identifiers
IX_EXTERNAL_IDS = 'externalIds'


class ValidatingExternalIdentifiers(object):
    """
    Fetch from any :class:`IExternalIdentifierUtility` registered for
    users and only store lowercase identifiers.
    """

    __slots__ = ('external_ids',)

    def _get_external_ids(self, user):
        result = set()
        id_utils = component.subscribers((user,),
                                         IExternalIdentifierUtility)
        for id_util in id_utils or ():
            external_id = id_util.get_namespaced_external_id(user)
            if external_id:
                result.add(external_id.lower())
        return result

    def __init__(self, obj, unused_default=None):
        if IUser.providedBy(obj):
            self.external_ids = self._get_external_ids(obj)

    def __reduce__(self):
        raise TypeError()


class ExternalIdIndex(AttributeSetIndex):
    default_field_name = 'external_ids'
    default_interface = ValidatingExternalIdentifiers


class ExternalIdentifierCatalog(Catalog):
    pass


def create_identifier_catalog(catalog=None, family=BTrees.family64):
    catalog = ExternalIdentifierCatalog(family=family) if catalog is None else catalog
    for name, clazz in ((IX_EXTERNAL_IDS, ExternalIdIndex),):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def get_identifier_catalog(registry=component):
    return registry.queryUtility(ICatalog, name=CATALOG_NAME)


def install_identifiers_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_identifier_catalog(registry=lsm)
    if catalog is not None:
        return catalog

    catalog = ExternalIdentifierCatalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog, provided=ICatalog, name=CATALOG_NAME)

    catalog = create_identifier_catalog(catalog=catalog, family=intids.family)
    for index in catalog.values():
        intids.register(index)
    return catalog
