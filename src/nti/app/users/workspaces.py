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

from zope.traversing.interfaces import IPathAdapter

from pyramid.interfaces import IRequest

from nti.app.users.interfaces import ICommunitiesWorkspace
from nti.app.users.interfaces import IAllCommunitiesCollection
from nti.app.users.interfaces import IJoinedCommunitiesCollection
from nti.app.users.interfaces import IAdministeredCommunitiesCollection

from nti.appserver.workspaces import NameFilterableMixin
from nti.appserver.workspaces import AbstractPseudoMembershipContainer

from nti.appserver.workspaces.interfaces import IUserService

from nti.coremetadata.interfaces import IDeactivatedCommunity

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.communities import Community

from nti.dataserver.users.interfaces import IDisallowMembershipOperations

from nti.dataserver.users.utils import get_communities_by_site

from nti.externalization.interfaces import StandardExternalFields

from nti.property.property import alias

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICommunitiesWorkspace)
class _CommunitiesWorkspace(Contained):

    __name__ = 'Communities'

    name = alias('__name__', __name__)

    def __init__(self, user_service):
        self.context = user_service
        self.user = user_service.user

    @Lazy
    def collections(self):
        return (AllCommunitiesCollection(self),
                JoinedCommunitiesCollection(self),
                AdministeredCommunitiesCollection(self))

    def __getitem__(self, key):
        for i in self.collections:
            if i.__name__ == key:
                return i
        raise KeyError(key)

    def __len__(self):
        return len(self.collections)


@component.adapter(IUserService)
@interface.implementer(ICommunitiesWorkspace)
def _user_communities_workspace(user_service):
    result = _CommunitiesWorkspace(user_service)
    result.__parent__ = result.user
    return result


@interface.implementer(IPathAdapter)
@component.adapter(IUser, IRequest)
def CommunitiesPathAdapter(context, unused_request=None):
    service = IUserService(context)
    workspace = ICommunitiesWorkspace(service)
    return workspace


@component.adapter(ICommunitiesWorkspace)
@interface.implementer(IJoinedCommunitiesCollection)
class JoinedCommunitiesCollection(AbstractPseudoMembershipContainer,
                                  NameFilterableMixin):

    name = u'Communities'
    __name__ = name

    def __init__(self, communities_ws):
        super(JoinedCommunitiesCollection, self).__init__(communities_ws)
        self.__parent__ = communities_ws

    @property
    def memberships(self):
        return self._user.dynamic_memberships

    def selector(self, obj):
        """
        Communities that allow membership ops and are either public or
        we are a member of.
        """
        return ICommunity.providedBy(obj) \
           and not IDeactivatedCommunity.providedBy(obj) \
           and not IDisallowMembershipOperations.providedBy(obj) \
           and (obj.public or self.remote_user in obj) \
           and self.search_include(obj)


@component.adapter(IUser)
@interface.implementer(IJoinedCommunitiesCollection)
def _UserCommunitiesCollectionFactory(user):
    return JoinedCommunitiesCollection(CommunitiesPathAdapter(user))


@component.adapter(ICommunitiesWorkspace)
@interface.implementer(IAllCommunitiesCollection)
class AllCommunitiesCollection(AbstractPseudoMembershipContainer,
                               NameFilterableMixin):

    name = u'AllCommunities'
    __name__ = name

    def __init__(self, communities_ws):
        super(AllCommunitiesCollection, self).__init__(communities_ws)
        self.__parent__ = communities_ws

    @property
    def accepts(self):
        if      self.remote_user == self._user \
            and is_admin_or_site_admin(self.remote_user):
            return (Community.mime_type,)
        return ()

    @property
    def memberships(self):
        return get_communities_by_site()

    def selector(self, obj):
        """
        Communities you can possibly join that the user is not a member of.
        """
        return not IDisallowMembershipOperations.providedBy(obj) \
           and obj.public and obj.joinable \
           and self.search_include(obj) \
           and self._user not in obj


@component.adapter(IUser)
@interface.implementer(IAllCommunitiesCollection)
def _UserAllCommunitiesCollectionFactory(user):
    return AllCommunitiesCollection(CommunitiesPathAdapter(user))


@component.adapter(ICommunitiesWorkspace)
@interface.implementer(IAdministeredCommunitiesCollection)
class AdministeredCommunitiesCollection(AbstractPseudoMembershipContainer,
                                        NameFilterableMixin):

    __name__ = u'AdministeredCommunities'

    name = alias('__name__', __name__)

    accepts = ()
    links = ()

    def __init__(self, communities_ws):
        super(AdministeredCommunitiesCollection, self).__init__(communities_ws)
        self.__parent__ = communities_ws

    def selector(self, obj):
        # IDisallowMembershipOperations are communities
        # (e.g. ICourseInstanceSharingScopes) that we do not want to expose
        # in community workspaces.
        return  not IDisallowMembershipOperations.providedBy(obj) \
            and self.search_include(obj)

    @property
    def memberships(self):
        _is_admin = is_admin(self.remote_user)
        communities = get_communities_by_site()
        return [x for x in communities or () if _is_admin or x.is_admin(self._user)]


@component.adapter(IUser)
@interface.implementer(IAdministeredCommunitiesCollection)
def _UserAdministeredCommunitiesCollectionFactory(user):
    return AdministeredCommunitiesCollection(CommunitiesPathAdapter(user))
