#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,inconsistent-mro

from zope import schema
from zope import interface
from zope import deferredimport

from zope.location.interfaces import ILocation

from zope.security.interfaces import IPrincipal

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IContainer

from nti.schema.field import Object
from nti.schema.field import IndexedIterable as TypedIterable

# OData-inspired objects related to retrieving
# data for portions of the URL space


class ICollection(ILocation):
    """
    A collection (in the Atom sense) contains individual objects (entries).
    It may be writable.
    """
    name = schema.TextLine(title=u"The name of this collection.")

    accepts = interface.Attribute(
        """
        An iterable of types or interfaces this container will
        accept the addition of. If None, this container will accept
        any valid type. If present but empty, this container will not
        accept any input.
        """)


class IContainerCollection(ICollection):
    """
    An :class:`ICollection` based of an :class:`nti.dataserver.interfaces.IContainer`.
    """

    container = Object(IContainer,
                       title=u"The backing container",
                       readonly=True)


class IWorkspace(ILocation):
    """
    A workspace (in the Atom sense) is a collection of collections.
    Collections can exist in multiple workspaces. A collection
    is also known as a feed (again, in the Atom sense).

    Workspaces should generally either be traversable by default
    (providing a ``__getitem__``) or provide an adapter to ``ITraversable``
    for their collections.
    """
    name = schema.TextLine(title=u"The name of this workspace.")

    collections = TypedIterable(title=u"The collections of this workspace.",
                                readonly=True,
                                value_type=Object(ICollection, title=u"A collection in this workspace"))


class IService(ILocation):
    """
    A service (in the Atom sense) is a collection of workspaces.
    """

    workspaces = TypedIterable(title=u"The workspaces of this service",
                               value_type=Object(IWorkspace, title=u"Workspaces in the service"))

    principal = Object(IPrincipal,
                       title=u'The principal',
                       description=u"the principal of this service",
                       required=False)


class IWorkspaceValidator(interface.Interface):
    """
    Marker interface for utility that validates a workspace before
    it is made avaiable in a user's service
    """

    def validate(workspace):
        """
        returns True if the workspace is valid
        """


class IUserWorkspace(IWorkspace):
    """
    A workspace for a particular user.
    """
    user = Object(IUser, title=u"The user")


class ICatalogWorkspace(IWorkspace):
    """
    A workspace to provide (possibly) heterogeneous catalog choices for a user.
    """
    principal = Object(IPrincipal,
                       title=u'The principal',
                       description=u"the principal of this workspace",
                       required=False)


class ICatalogWorkspaceLinkProvider(interface.Interface):

    def links(workspace):
        """
        return an iterable of catalog links
        """


class ICatalogCollection(IContainerCollection):
    """
    A collection contained within the :class:``ICatalogWorkspace``.
    """


class ICatalogCollectionProvider(interface.Interface):
    """
    A provider of :class:``ICatalogCollection`` items.
    """

    def get_collection_iter(filter_string=None):
        """
        Returns an iterable over this collection provider, optionally
        filtering on the given string.
        """


class IFeaturedCatalogCollectionProvider(ICatalogCollectionProvider):
    """
    An :class:``ICatalogCollectionProvider`` that provides `featured` items.
    """


class IPurchasedCatalogCollectionProvider(ICatalogCollectionProvider):
    """
    An :class:``ICatalogCollectionProvider`` that provides `purchased` items.
    """


class IUserWorkspaceLinkProvider(interface.Interface):

    def links(workspace):
        """
        return an iterable of user workspace links
        """


class IGlobalCollection(ICollection):
    """
    A collection contained within the Global :class:``IWorkspace``.
    """


class IGlobalWorkspaceLinkProvider(interface.Interface):

    def links(workspace):
        """
        return an iterable of global workspace links
        """


class IUserService(IService):
    """
    A service for a particular user.
    """
    user_workspace = Object(IUserWorkspace,
                            title=u"The main workspace for the user")


deferredimport.initialize()
deferredimport.deprecatedFrom(
    "Moved to nti.app.contentlibrary.workspaces.interfaces ",
    "nti.app.contentlibrary.workspaces.interfaces",
    "ILibraryCollection")
