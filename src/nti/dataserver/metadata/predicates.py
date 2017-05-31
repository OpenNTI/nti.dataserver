#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IIntIdIterable
from nti.dataserver.interfaces import ISystemUserPrincipal
from nti.dataserver.interfaces import IPrincipalMetadataObjects
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata.utils import get_iid

from nti.dataserver.metadata.utils import user_messageinfo_iter_objects


@interface.implementer(IIntIdIterable, IPrincipalMetadataObjects)
class BasePrincipalObjects(object):

    def __init__(self, user=None, *args, **kwargs):
        self.user = user

    def iter_intids(self, intids=None):
        seen = set()
        for obj in self.iter_objects():
            uid = get_iid(obj, intids=intids)
            if uid is not None and uid not in seen:
                seen.add(uid)
                yield uid

    def iter_objects(self):
        raise NotImplementedError()


@component.adapter(IUser)
class _ContainedPrincipalObjects(BasePrincipalObjects):

    def iter_objects(self):
        user = self.user
        for obj in user.iter_objects(only_ntiid_containers=True):
            yield obj


@component.adapter(IUser)
class _FriendsListsPrincipalObjects(BasePrincipalObjects):

    def iter_objects(self):
        for obj in self.user.friendsLists.values():
            yield obj


@component.adapter(IUser)
@interface.implementer(IPrincipalMetadataObjects)
class _MessageInfoPrincipalObjects(BasePrincipalObjects):

    def iter_objects(self):
        for obj in user_messageinfo_iter_objects(self.user):
            yield obj


@component.adapter(IUser)
class _MeetingPrincipalObjects(BasePrincipalObjects):

    def iter_objects(self):
        storage = IUserTranscriptStorage(self.user)
        for meeting in storage.meetings:
            yield meeting


@component.adapter(IUser)
class _DFLBlogObjects(BasePrincipalObjects):

    def iter_objects(self):
        for membership in self.user.dynamic_memberships:
            if not IDynamicSharingTargetFriendsList.providedBy(membership):
                continue
            board = IDFLBoard(membership, None)
            if not board:
                continue
            yield board
            for forum in board.values():
                yield forum
                for topic in forum.values():
                    yield topic
                    for comment in topic.values():
                        yield comment


@component.adapter(ISystemUserPrincipal)
class _CommunityBlogObjects(BasePrincipalObjects):

    def iter_communities(self):
        dataserver = component.getUtility(IDataserver)
        entities = IShardLayout(dataserver).users_folder
        for entity in entities.values():
            if not ICommunity.providedBy(entity):
                continue
            yield entity

    def iter_objects(self, intids=None):
        for community in self.iter_communities():
            board = ICommunityBoard(community, None)
            if not board:
                continue
            yield board
            for forum in board.values():
                yield forum
                for topic in forum.values():
                    yield topic
                    for comment in topic.values():
                        yield comment
