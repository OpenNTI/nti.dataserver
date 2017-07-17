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

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import CachedProperty

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.coremetadata.interfaces import SYSTEM_USER_ID
from nti.coremetadata.interfaces import SYSTEM_USER_NAME

from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IIntIdIterable
from nti.dataserver.interfaces import ISystemUserPrincipal
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata.interfaces import IPrincipalMetadataObjects

from nti.dataserver.metadata.utils import queryId
from nti.dataserver.metadata.utils import user_messageinfo_iter_objects


@interface.implementer(IIntIdIterable, IPrincipalMetadataObjects)
class BasePrincipalObjects(object):

    system_users = (None, '', SYSTEM_USER_ID, SYSTEM_USER_NAME)

    def __init__(self, user=None):
        self.user = user

    @Lazy
    def username(self):
        result = getattr(self.user, 'username', self.user)
        return (getattr(result, 'id', result) or '').lower()

    @CachedProperty
    def users_folder(self):
        dataserver = component.getUtility(IDataserver)
        return IShardLayout(dataserver).users_folder

    def creator(self, item):
        creator = getattr(item, 'creator', item)
        creator = getattr(creator, 'username', creator)
        creator = getattr(creator, 'id', creator)
        creator = None if creator is item else creator
        if creator and creator in self.users_folder:
            return creator.lower()
        return None

    def is_system_username(self, name):
        return name in self.system_users

    def iter_intids(self, intids=None):
        for obj in self.iter_objects():
            uid = queryId(obj, intids=intids)
            if uid is not None:
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


class BoardObjectsMixin(object):

    def forum_objects(self, forum):
        yield forum
        for topic in forum.values():
            yield topic
            yield topic.headline
            for comment in topic.values():
                yield comment

    def board_objects(self, board):
        yield board
        for forum in board.values():
            for obj in self.forum_objects(forum):
                yield obj


@component.adapter(IUser)
class _SelfUserObjects(BasePrincipalObjects):

    def iter_objects(self):
        yield self.user


@component.adapter(IUser)
class _PersonalBlogObjects(BasePrincipalObjects, BoardObjectsMixin):

    def iter_objects(self):
        blog = IPersonalBlog(self.user, None)
        if blog:
            return self.forum_objects(blog)
        return ()


@component.adapter(IUser)
class _DFLBlogObjects(BasePrincipalObjects, BoardObjectsMixin):

    def iter_objects(self):
        for membership in self.user.dynamic_memberships:
            if not IDynamicSharingTargetFriendsList.providedBy(membership):
                continue
            board = IDFLBoard(membership, None)
            if board is not None:
                for obj in self.board_objects(board):
                    yield obj


@component.adapter(ISystemUserPrincipal)
class _CommunityBlogObjects(BasePrincipalObjects, BoardObjectsMixin):

    def iter_communities(self):
        for entity in self.users_folder.values():
            if not ICommunity.providedBy(entity):
                continue
            yield entity

    def iter_objects(self):
        for community in self.iter_communities():
            board = ICommunityBoard(community, None)
            if board is not None:
                for obj in self.board_objects(board):
                    yield obj
