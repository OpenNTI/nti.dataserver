#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import six
from nti.contentfragments.interfaces import IPlainTextContentFragment

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component import subscribers

from nti.coremetadata.interfaces import ICommunity

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import IForumTypeCreatedNotificationUsers
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic

from nti.dataserver.contenttypes.forums.notification import send_creation_notification_email

from nti.dataserver.job.email import AbstractEmailJob

from nti.dataserver.job.interfaces import IScheduledJob

from nti.dataserver.users import User

from nti.mailer.interfaces import IEmailAddressable

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.traversal.traversal import find_interface

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


DEFAULT_EMAIL_DEFER_TIME = 60  # 1 minute


@interface.implementer(IScheduledJob)
class AbstractForumTypeScheduledEmailJob(AbstractEmailJob):

    execution_buffer = DEFAULT_EMAIL_DEFER_TIME

    @Lazy
    def execution_time(self):
        return self.utc_now + self.execution_buffer

    def get_usernames(self, obj):
        usernames = set()
        for subscriber in subscribers((obj,), IForumTypeCreatedNotificationUsers):
            subscriber_usernames = subscriber.get_usernames()
            usernames = usernames.union(subscriber_usernames)
        return usernames

    def _emails_from_usernames(self, usernames):
        emails = []
        for username in usernames:
            user = User.get_user(username)
            email = IEmailAddressable(user, None)
            if email is None:
                logger.debug(u'Username %s does not have an email address for notification' % username)
                continue
            emails.append(email.email)
        return emails

    def _do_call(self, obj, usernames):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        object_ntiid = kwargs.get('obj_ntiid')
        obj = find_object_with_ntiid(object_ntiid)
        if obj is None:
            logger.debug(u'Object with ntiid %s no longer exists' % object_ntiid)
            return
        usernames = self.get_usernames(obj)
        self._do_call(obj, usernames)


@component.adapter(IHeadlineTopic)
class HeadlineTopicCreatedDeferredEmailJob(AbstractForumTypeScheduledEmailJob):

    def _post_to_html(self, post):
        html = u''
        for part in post.body:
            if isinstance(part, six.string_types):
                plain_text = IPlainTextContentFragment(part)
                div = u'<div>%s</div>' % plain_text
                html += div
        return html

    def _do_call(self, topic, usernames):
        title = topic.title
        forum = find_interface(topic, IForum)
        forum_title = forum.title
        subject = u'Discussion %s created in %s' % (title, forum_title)
        emails = self._emails_from_usernames(usernames)
        message = self._post_to_html(topic.headline)
        for email in emails:
            send_creation_notification_email(topic,
                                             sender=topic.creator,
                                             receiver_emails=[email],
                                             subject=subject,
                                             message=message)


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
