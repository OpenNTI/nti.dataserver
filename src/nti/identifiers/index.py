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

from zope.catalog.interfaces import ICatalog

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.coremetadata.interfaces import IUser

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex

CATALOG_NAME = 'nti.dataserver.++etc++external-identifier-catalog'

#: Site
IX_SITE = 'site'

#: External identifiers
IX_EXTERNAL_IDS = 'externalIds'

#: External type strings
IX_EXTERNAL_TYPES = 'externalTypes'

logger = __import__('logging').getLogger(__name__)


class ValidatingExternalIdentifiers(object):
    """
    Fetch all external_ids from :class:`IUserExternalIdentityContainer`
    for our user.
    """

    __slots__ = ('external_ids',)

    def _get_external_ids(self, user):
        external_container = IUserExternalIdentityContainer(user, None)
        if external_container is not None:
            return set(x.lower() for x in external_container.values())

    def __init__(self, obj, unused_default=None):
        if IUser.providedBy(obj):
            self.external_ids = self._get_external_ids(obj)

    def __reduce__(self):
        raise TypeError()


class ValidatingExternalTypes(object):
    """
    Fetch all external_types from :class:`IUserExternalIdentityContainer`
    for our user.
    """

    __slots__ = ('external_types',)

    def _get_external_types(self, user):
        external_container = IUserExternalIdentityContainer(user, None)
        if external_container is not None:
            return set(x.lower() for x in external_container)

    def __init__(self, obj, unused_default=None):
        if IUser.providedBy(obj):
            self.external_types = self._get_external_types(obj)

    def __reduce__(self):
        raise TypeError()


class ValidatingSiteName(object):
    """
    XXX: We should enforce that this user does not map to another site
    since this is something we do not support.
    """

    __slots__ = ('site',)

    def __init__(self, obj, unused_default=None):
        if IUser.providedBy(obj):
            self.site = getattr(getSite(), '__name__', None)

    def __reduce__(self):
        raise TypeError()


class SingleSiteIndex(ValueIndex):
    default_field_name = 'site'
    default_interface = ValidatingSiteName


class ExternalIdIndex(AttributeSetIndex):
    default_field_name = 'external_ids'
    default_interface = ValidatingExternalIdentifiers


class ExternalTypesIndex(AttributeSetIndex):
    default_field_name = 'external_types'
    default_interface = ValidatingExternalTypes


class ExternalIdentifierCatalog(Catalog):
    pass


def create_identifier_catalog(catalog=None, family=BTrees.family64):
    catalog = ExternalIdentifierCatalog(family=family) if catalog is None else catalog
    for name, clazz in ((IX_SITE, SingleSiteIndex),
                        (IX_EXTERNAL_IDS, ExternalIdIndex),
                        (IX_EXTERNAL_TYPES, ExternalTypesIndex),):
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
