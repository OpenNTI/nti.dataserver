#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component
from zope import interface

from zope.component import subscribers

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.coremetadata.interfaces import ICommunity

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import IForumTypeUsers
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.job import AbstractEmailJob
from nti.dataserver.job import ScheduledEmailJobMixin

from nti.traversal.traversal import find_interface

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


DEFAULT_EMAIL_BUFFER_TIME = 60  # 1 minute


class AbstractForumTypeScheduledEmailJob(AbstractEmailJob, ScheduledEmailJobMixin):

    execution_buffer = DEFAULT_EMAIL_BUFFER_TIME

    def get_users(self):
        users = []
        for subscriber in subscribers((self.obj,), IForumTypeUsers):
            subscriber_users = subscriber.get_users()
            users.extend(subscriber_users)


@component.adapter(IForum)
class ForumCreatedScheduledEmailJob(AbstractForumTypeScheduledEmailJob):

    def __call__(self, *args, **kwargs):
        users = self.get_users()


@component.adapter(ITopic)
class TopicCreatedScheduledEmailJob(AbstractForumTypeScheduledEmailJob):

    def __call__(self, *args, **kwargs):
        users = self.get_users()


@interface.implementer(IForumTypeUsers)
class AbstractUsersForForumType(object):

    leaf_iface = None

    def __init__(self, context):
        self.context = context

    def _users_for_type(self, container):
        raise NotImplementedError

    def get_users(self):
        container = find_interface(self.context, self.leaf_iface)
        if container is not None:
            return self._users_for_type(container)


class CourseUsersForForumType(AbstractUsersForForumType):

    leaf_iface = ICourseInstance

    def _users_for_type(self, course):
        return []


class CommunityUsersForForumType(AbstractUsersForForumType):

    leaf_iface = ICommunity

    def _users_for_type(self, community):
        return []
