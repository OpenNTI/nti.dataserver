#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of an Atom/OData workspace and collection for courses.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from zope.location.interfaces import IRoot
from zope.location.interfaces import ILocationInfo

from zope.location.traversing import LocationPhysicallyLocatable

from pyramid.threadlocal import get_current_request

from nti.app.users.interfaces import ICommunitiesWorkspace
from nti.app.users.interfaces import IAllCommunitiesCollection
from nti.app.users.interfaces import IJoinedCommunitiesCollection
from nti.app.users.interfaces import ICommunitiesWorkspaceLinkProvider
from nti.app.users.interfaces import IAdministeredCommunitiesCollection

from nti.appserver.workspaces import NameFilterableMixin
from nti.appserver.workspaces import UserEnumerationWorkspace
from nti.appserver.workspaces import AbstractPseudoMembershipContainer

from nti.appserver.workspaces.interfaces import IUserService
from nti.appserver.workspaces.interfaces import IUserWorkspace
from nti.appserver.workspaces.interfaces import IContainerCollection

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_DELETE

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IHiddenMembership
from nti.dataserver.users.interfaces import IDisallowMembershipOperations

from nti.dataserver.users.utils import get_communities_by_site

from nti.datastructures.datastructures import LastModifiedCopyingUserList

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

from nti.ntiids.oids import to_external_ntiid_oid

from nti.property.property import alias

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICommunitiesWorkspace)
class _CommunitiesWorkspace(Contained):

    #: Our name, part of our URL
    __name__ = 'Communities'

    name = alias('__name__', __name__)

    def __init__(self, user_service):
        self.context = user_service
        self.user = user_service.user

    @Lazy
    def collections(self):
        """
        The collections in this workspace provide info about the enrolled and
        available courses as well as any courses the user administers (teaches).
        """
        return (AllCommunitiesCollection(self),
                JoinedCommunitiesCollection(self),
                AdministeredCommunitiesCollection(self))

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
@interface.implementer(ICommunitiesWorkspace)
def _user_communities_workspace(user_service):
    """
    The courses for a user reside at the path ``/users/$ME/Communities``.
    """
    result = _CommunitiesWorkspace(user_service)
    result.__parent__ = result.user
    return result


@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
class JoinedCommunitiesCollection(AbstractPseudoMembershipContainer,
                                  NameFilterableMixin):

    name = u'Communities'
    __name__ = name

    @property
    def memberships(self):
        return self._user.dynamic_memberships

    def selector(self, obj):
        """
        Communities that allow membership ops and are either public or
        we are a member of.
        """
        return ICommunity.providedBy(obj) \
           and not IDisallowMembershipOperations.providedBy(obj) \
           and (obj.public or self.remote_user in obj) \
           and self.search_include(obj)


@component.adapter(IUser)
@interface.implementer(IContainerCollection)
def _UserCommunitiesCollectionFactory(user):
    return JoinedCommunitiesCollection(UserEnumerationWorkspace(user))


@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
class AllCommunitiesCollection(AbstractPseudoMembershipContainer,
                               NameFilterableMixin):

    name = u'AllCommunities'
    __name__ = name

    @property
    def memberships(self):
        # Not yet implemented.  Need all visible communities.
        return self._user.dynamic_memberships

    def selector(self, obj):
        """
        Communities you're a member of plus communities
        """
        return ICommunity.providedBy(obj) \
           and not IDisallowMembershipOperations.providedBy(obj) \
           and (obj.public or self.remote_user in obj) \
           and self.search_include(obj)


@component.adapter(IUser)
@interface.implementer(IContainerCollection)
def _UserAllCommunitiesCollectionFactory(user):
    return AllCommunitiesCollection(UserEnumerationWorkspace(user))
