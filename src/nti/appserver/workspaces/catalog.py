#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Service document and user workspaces support.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import interface

from zope.authentication.interfaces import IUnauthenticatedPrincipal

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

from pyramid.interfaces import IRequest

from pyramid.threadlocal import get_current_request

from nti.appserver.workspaces.interfaces import IService
from nti.appserver.workspaces.interfaces import IUserService
from nti.appserver.workspaces.interfaces import ICatalogWorkspace
from nti.appserver.workspaces.interfaces import ICatalogCollection
from nti.appserver.workspaces.interfaces import ICatalogWorkspaceLinkProvider
from nti.appserver.workspaces.interfaces import IPurchasedCatalogCollectionProvider

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

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
        self.user = IUser(catalog_workspace.principal, None)

    @Lazy
    def _params(self):
        result = {}
        request = get_current_request()
        if request is not None:
            values = request.params
            result = CaseInsensitiveDict(values)
        return result

    @Lazy
    def filter_str(self):
        result = self._params.get('filter')
        return result and result.lower()

    @property
    def container(self):
        providers = component.subscribers((self.user,),
                                          IPurchasedCatalogCollectionProvider)
        result = LocatedExternalList()
        for provider in providers:
            provider_iter = provider.get_collection_iter(self.filter_str)
            result.extend(provider_iter)
        result.__name__ = self.__name__
        result.__parent__ = self.__parent__
        result.lastModified = None
        return result


@interface.implementer(IPathAdapter)
@component.adapter(IDataserverFolder, IRequest)
def DataserverCatalogPathAdapter(unused_context, request):
    user = request.remote_user
    if user is None:
        user = component.queryUtility(IUnauthenticatedPrincipal)
    service = IService(user)
    workspace = ICatalogWorkspace(service)
    return workspace


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

    def __init__(self, principal):
        super(CatalogWorkspace, self).__init__()
        if IUser.providedBy(principal):
            self.__parent__ = principal
        else:
            # Principals do not have a useful lineage
            self.__parent__ = component.getUtility(IDataserver).dataserver_folder
        self.principal = principal

    @property
    def links(self):
        result = []
        for provider in component.subscribers((self.principal,), ICatalogWorkspaceLinkProvider):
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

    def __acl__(self):
        acl = acl_from_aces(
            ace_allowing(self.principal,
                         ACT_READ,
                         CatalogWorkspace)
        )
        return acl


@component.adapter(IService)
@interface.implementer(ICatalogWorkspace)
def _catalog_workspace(service):
    catalog_workspace = CatalogWorkspace(service.principal)
    return catalog_workspace
