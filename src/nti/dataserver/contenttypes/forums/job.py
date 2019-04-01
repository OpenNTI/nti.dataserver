#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import six

from pyramid.threadlocal import get_current_request

from six.moves import urllib_parse

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component import subscribers

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.coremetadata.interfaces import ICommunity

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import IForumTypeCreatedNotificationUsers
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic

from nti.dataserver.contenttypes.forums.notification import send_creation_notification_email

from nti.dataserver.job.decorators import RunJobInSite

from nti.dataserver.job.job import AbstractJob

from nti.dataserver.job.interfaces import IScheduledJob

from nti.dataserver.users import User

from nti.links import Link
from nti.links import render_link

from nti.mailer.interfaces import IEmailAddressable

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


DEFAULT_EMAIL_DEFER_TIME = 60  # 1 minute


@interface.implementer(IScheduledJob)
class AbstractForumTypeScheduledEmailJob(AbstractJob):

    execution_buffer = DEFAULT_EMAIL_DEFER_TIME

    def __init__(self, obj):
        super(AbstractForumTypeScheduledEmailJob, self).__init__(obj)
        request = get_current_request()
        self.job_kwargs['application_url'] = request.application_url

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
            if email is None or email.email is None:
                logger.debug(u'Username %s does not have an email address for notification' % username)
                continue
            emails.append(email.email)
        return emails

    def _do_call(self, obj, usernames):
        raise NotImplementedError

    @RunJobInSite
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
                html += ' %s' % plain_text
        return html.strip()

    def _url_to_obj(self, obj):
        application_url = self.job_kwargs['application_url']

        rendered_link = render_link(Link(obj))
        if rendered_link is None:
            logger.warn(u'Unable to generate link for %s' % obj)
            raise ValueError(u'Unable to generate link for %s' % obj)

        href = rendered_link.get('href', None)
        if href is None:
            logger.warn(u'No href for %s' % obj)
            raise ValueError(u'No href for %s' % obj)

        url = urllib_parse.urljoin(application_url, href)
        return url

    def _do_call(self, topic, usernames):
        title = topic.title
        forum = find_interface(topic, IForum)
        forum_title = forum.title
        subject = u'Discussion %s created in %s' % (title, forum_title)
        emails = self._emails_from_usernames(usernames)
        message = self._post_to_html(topic.headline)
        avatar_url = self._url_to_obj(topic.creator)
        avatar_url = avatar_url if avatar_url.endswith('/') else avatar_url + '/'
        avatar_url = urllib_parse.urljoin(avatar_url, u'@@avatar')

        topic_url = urllib_parse.urljoin(self.job_kwargs['application_url'], '/app/id/%s' % topic.NTIID)
        for email in emails:
            send_creation_notification_email(sender=topic.creator,
                                             receiver_emails=[email],
                                             subject=subject,
                                             message=message,
                                             request=self.get_request(topic),
                                             forum_type_obj_url=topic_url,
                                             avatar_url=avatar_url)
        logger.info("Sending board object notification email (%s) (ntiid=%s) (forum=%s) (email_count=%s)",
                    title,
                    topic.NTIID,
                    forum.title,
                    len(emails))


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
