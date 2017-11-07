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

from zope.traversing.interfaces import IPathAdapter

from pyramid.interfaces import IRequest

from nti.appserver.workspaces.interfaces import IUserService
from nti.appserver.workspaces.interfaces import ICatalogWorkspace
from nti.appserver.workspaces.interfaces import ICatalogCollection
from nti.appserver.workspaces.interfaces import ICatalogWorkspaceLinkProvider
from nti.appserver.workspaces.interfaces import IPurchasedCatalogCollectionProvider

from nti.dataserver.interfaces import IUser

from nti.externalization.interfaces import LocatedExternalList
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
        result = LocatedExternalList()
        for provider in providers:
            provider_iter = provider.get_collection_iter()
            result.extend(provider_iter)
        result.__name__ = self.__name__
        result.__parent__ = self.__parent__
        result.lastModified = None
        return result


@interface.implementer(IPathAdapter)
@component.adapter(IUser, IRequest)
def CatalogPathAdapter(context, unused_request):
    service = IUserService(context)
    workspace = ICatalogWorkspace(service)
    return workspace


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

    @property
    def links(self):
        result = []
        for provider in component.subscribers((self.user,), ICatalogWorkspaceLinkProvider):
            links = provider.links(self)
            result.extend(links or ())
        return result

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

    def __getitem__(self, key):
        """
        Make us traversable to collections.
        """
        for i in self.collections:
            if i.__name__ == key:
                return i
        raise KeyError(key)

    def __len__(self):
        return len(self.collections)


@component.adapter(IUserService)
@interface.implementer(ICatalogWorkspace)
def _catalog_workspace(user_service):
    catalog_workspace = CatalogWorkspace(user_service.user)
    return catalog_workspace

