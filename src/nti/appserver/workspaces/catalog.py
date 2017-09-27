#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Service document and user workspaces support.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from nti.appserver.workspaces.interfaces import IUserService
from nti.appserver.workspaces.interfaces import ICatalogWorkspace
from nti.appserver.workspaces.interfaces import ICatalogCollection
from nti.appserver.workspaces.interfaces import IFeaturedCatalogCollectionProvider
from nti.appserver.workspaces.interfaces import IPurchasedCatalogCollectionProvider

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.property.property import alias

logger = __import__('logging').getLogger(__name__)

ITEMS = StandardExternalFields.ITEMS


@component.adapter(ICatalogWorkspace)
@interface.implementer(ICatalogCollection)
class PurchasedCatalogCollection(Contained):
    """
    A catalog collection that returns 'purchased' items.
    """

    name = 'Purchased'
    __name__ = name
    _workspace = alias('__parent__')
    accepts = ()
    links = ()

    def __init__(self, catalog_workspace):
        self.__parent__ = catalog_workspace

    @property
    def _user(self):
        return self._workspace.user

    @property
    def container(self):
        providers = component.subscribers((self._user,),
                                          IPurchasedCatalogCollectionProvider)
        result = LocatedExternalDict()
        result[ITEMS] = featured_items = []
        for provider in providers:
            provider_iter = provider.get_collection_iter()
            featured_items.extend(provider_iter)
        return result


@component.adapter(ICatalogWorkspace)
@interface.implementer(ICatalogCollection)
class FeaturedCatalogCollection(Contained):
    """
    A catalog collection that returns 'featured' items.
    """

    name = 'Featured'
    __name__ = name
    _workspace = alias('__parent__')
    accepts = ()
    links = ()

    def __init__(self, catalog_workspace):
        self.__parent__ = catalog_workspace

    @property
    def _user(self):
        return self._workspace.user

    @property
    def container(self):
        providers = component.subscribers((self._user,),
                                          IFeaturedCatalogCollectionProvider)
        result = LocatedExternalDict()
        result[ITEMS] = featured_items = []
        for provider in providers:
            provider_iter = provider.get_collection_iter()
            featured_items.extend(provider_iter)
        return result


@interface.implementer(ICatalogWorkspace)
class CatalogWorkspace(Contained):
    """
    A heterogeneous workspace that combines various `catalog` like collections
    that users may be be interested in joining.
    """

    __name__ = 'Catalog'

    name = alias('__name__', __name__)
    links = ()

    def __init__(self, user):
        super(CatalogWorkspace, self).__init__()
        self.__parent__ = user
        self.user = user

    @Lazy
    def collections(self):
        """
        The returned collections are sorted by name.
        """
        result = []
        for catalog_collection in component.subscribers((self,),
                                                        ICatalogCollection):
            result.append(catalog_collection)
        return sorted(result, key=lambda x: x.name)


@interface.implementer(ICatalogWorkspace)
@component.adapter(IUserService)
def _catalog_workspace(user_service):
    catalog_workspace = CatalogWorkspace(user_service.user)
    return catalog_workspace

