#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component
from zope import interface

from zope.component import subscribers

from nti.coremetadata.interfaces import ICommunity

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import IForumTypeCreatedNotificationUsers
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.job.email import AbstractEmailJob
from nti.dataserver.job.email import ScheduledEmailJobMixin

from nti.traversal.traversal import find_interface

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


DEFAULT_EMAIL_BUFFER_TIME = 60  # 1 minute


class AbstractForumTypeScheduledEmailJob(AbstractEmailJob, ScheduledEmailJobMixin):

    execution_buffer = DEFAULT_EMAIL_BUFFER_TIME

    def get_usernames(self):
        usernames = set()
        for subscriber in subscribers((self.obj,), IForumTypeCreatedNotificationUsers):
            subscriber_usernames = subscriber.get_usernames()
            usernames = usernames.union(subscriber_usernames)
        return usernames


@component.adapter(IForum)
class ForumCreatedScheduledEmailJob(AbstractForumTypeScheduledEmailJob):

    def __call__(self, *args, **kwargs):
        users = self.get_usernames()
        # This method is currently incomplete


@component.adapter(ITopic)
class TopicCreatedScheduledEmailJob(AbstractForumTypeScheduledEmailJob):

    def __call__(self, *args, **kwargs):
        users = self.get_usernames()
        # This method is currently incomplete


@interface.implementer(IForumTypeCreatedNotificationUsers)
class AbstractUsersForForumType(object):

    leaf_iface = None

    def __init__(self, context):
        self.context = context

    def _users_for_type(self, container):
        raise NotImplementedError

    def get_usernames(self):
        container = find_interface(self.context, self.leaf_iface)
        if container is not None:
            return self._users_for_type(container)
        return set()


class CommunityUsersForForumType(AbstractUsersForForumType):

    leaf_iface = ICommunity

    def _users_for_type(self, community):
        return set(community.iter_member_usernames())
