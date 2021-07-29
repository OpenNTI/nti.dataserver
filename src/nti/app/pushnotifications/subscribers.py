#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division

from pyramid.threadlocal import get_current_request

from six.moves import urllib_parse

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.intid.interfaces import IIntIds

from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate

from nti.app import pushnotifications as push_pkg

from nti.app.pushnotifications import email_notifications_preference

from nti.app.pushnotifications.interfaces import IMailTemplateProvider

from nti.app.pushnotifications import MessageFactory as _
from nti.app.pushnotifications import digest_email

from nti.app.pushnotifications.utils import get_top_level_context

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.coremetadata.interfaces import IUser
from nti.coremetadata.interfaces import IEntity
from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import ICommentPost

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IStreamChangeAcceptedByUser

from nti.dataserver.users import User

from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import EmailAddresablePrincipal

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

from nti.threadable.interfaces import IThreadable

logger = __import__('logging').getLogger(__name__)


def _mailer():
    return component.getUtility(ITemplatedMailer)


def _is_subscribed(user, setting_name):
    with email_notifications_preference(user) as prefs:
        return getattr(prefs, setting_name)


def _is_subscribed_replies(user):
    return _is_subscribed(user, "immediate_threadable_reply")


def _is_subscribed_mentions(user):
    return _is_subscribed(user, "notify_on_mention")


def _display_name(user, request):
    return component.getMultiAdapter((user, request), IDisplayNameGenerator)()


def _is_mentioned(user, threadable):
    if not IMentionable.providedBy(threadable):
        return False

    return threadable.isMentionedDirectly(user)


def _get_topic_author(threadable):
    """
    Return author of topic
    """
    parent = getattr(threadable, '__parent__', None)
    if ITopic.providedBy(parent):
        return getattr(parent, 'creator', None)

    return None


def _in_reply_to_author(threadable):
    """
    Return the author (username) of the threadable or topic we're replying to,
    if this is a direct response to a topic
    """
    in_reply_to = threadable.inReplyTo

    in_reply_to_author = None
    if in_reply_to is None:
        if ICommentPost.providedBy(threadable):
            in_reply_to_author = _get_topic_author(threadable)
    elif IThreadable.providedBy(in_reply_to):
        in_reply_to_author = getattr(in_reply_to, 'creator', None)

    # See if a non-user entity is the creator of this obj
    if      IEntity.providedBy(in_reply_to_author) \
        and not IUser.providedBy(in_reply_to_author):
        return None
    in_reply_to_author = getattr(in_reply_to_author,
                                 'username',
                                 in_reply_to_author)
    return in_reply_to_author


def _threadable_added(threadable, unused_event):
    in_reply_to_author = _in_reply_to_author(threadable)

    if not in_reply_to_author:
        return

    obj_creator = getattr(threadable, 'creator', None)
    obj_creator = getattr(obj_creator, 'username', obj_creator)
    if obj_creator == in_reply_to_author:
        return

    user = User.get_user(in_reply_to_author)
    # User may be deleted or may prefer not to be notified
    if     user is None \
        or not _is_subscribed_replies(user) \
        or _is_mentioned(user, threadable):
        return

    request = get_current_request()

    intids = component.getUtility(IIntIds)
    intid = intids.getId(threadable)
    recipient = {'email': EmailAddresablePrincipal(user),
                 'template_args': [intid],
                 'display_name': _display_name(user, request),
                 'since': 0}

    delegate = component.getMultiAdapter((threadable.inReplyTo, request),
                                        IBulkEmailProcessDelegate,
                                        name="digest_email")
    subject = delegate.compute_subject_for_recipient(None)
    template_args = delegate.compute_template_args_for_recipient(recipient)
    template_args['notable_text'] = 'A user has replied to one of your comments.'

    # Currently we don't have a link for unsubscribing this email notification.
    template_args.pop('unsubscribe_link', None)

    text_template_extension=delegate.text_template_extension

    mailer = _mailer()
    mailer.queue_simple_html_text_email(delegate.template_name,
                                        subject=subject,
                                        recipients=[user],
                                        template_args=template_args,
                                        reply_to=None,
                                        package=push_pkg,
                                        text_template_extension=text_template_extension)


def _support_email():
    policy = component.getUtility(ISitePolicyUserEventListener)
    support_email = getattr(policy, 'SUPPORT_EMAIL',
                            'support@nextthought.com')
    return support_email


def _get_dataserver():
    return component.getUtility(IDataserver)


def _is_user_online(username):
    dataserver = _get_dataserver()
    try:
        return bool(dataserver.sessions and dataserver.sessions.get_sessions_by_owner(username))
    except KeyError:  # Hmm. session_storage.py reports some inconsistency errors sometimes. Which is bad
        logger.exception("Failed to get all sessions for owner %s", username)
        return False


class _AbstractMailTemplateProvider(object):

    template_name = None

    def __init__(self, context):
        self.context = context

    @property
    def template(self):
        return self.template_name


@component.adapter(IMentionable)
@interface.implementer(IMailTemplateProvider)
class TitledMailTemplateProvider(_AbstractMailTemplateProvider):
    template_name = u"mention_email"


@component.adapter(ICommentPost)
@interface.implementer(IMailTemplateProvider)
class CommentMailTemplateProvider(_AbstractMailTemplateProvider):
    template_name = u"mention_email_comment"


def url_with_fragment(url, fragment):
    url_parts = list(urllib_parse.urlparse(url))
    url_parts[5] = urllib_parse.quote(fragment)
    return urllib_parse.urlunparse(url_parts)


class _TemplateArgs(digest_email._TemplateArgs):

    @property
    def snippet(self):
        if      not hasattr(self._primary, "body") \
            and hasattr(self._primary, "headline") \
            and hasattr(self._primary.headline, "body"):
            return self.snippet_of(self._primary.headline.body)

        return self.snippet_of(self._primary.body)

    def snippet_of(self, body):
        if body and isinstance(body[0], basestring):
            text = IPlainTextContentFragment(body[0])
            if len(text) > self.max_snippet_len:
                text = text[:self.max_snippet_len] + '...'
            return text
        return ''

    @Lazy
    def __parent__(self):
        return _TemplateArgs((self._primary.__parent__,), self.request)
    
    @Lazy
    def container(self):
        try:
            container_id = self._primary.containerId
        except AttributeError:
            pass
        else:
            container = find_object_with_ntiid(container_id)
            if container:
                return _TemplateArgs((container,), self.request)
        return None

    def _app_href(self, obj):
        # Default to the most stable identifier we have. If
        # we can get an actual OID, use that as it's very specific,
        # otherwise see if the object has on opinion (which may expose
        # more details than we'd like...)
        ntiid = (to_external_ntiid_oid(obj, mask_creator=True)
                 or getattr(obj, 'NTIID', None))
        if ntiid:
            # The clients do not use the prefix.
            ntiid = ntiid.replace('tag:nextthought.com,2011-10:', '')
            return self.request.route_url('objects.generic.traversal',
                                          'id',
                                          ntiid,
                                          traverse=()).replace('/dataserver2',
                                                               self.web_root)

        # TODO: These don't actually do what we want in terms of interacting
        # with the application...
        return self.request.resource_url(obj)

    @property
    def creator_href(self):
        return self._app_href(self._primary.creator)

    @property
    def reply_href(self):
        return url_with_fragment(self._app_href(self._primary),
                                 "comment")


def _is_newly_mentioned(user, change):
    mentions_info = getattr(change, 'mentions_info', None)

    if mentions_info is None:
        return False

    result = user in change.mentions_info.new_effective_mentions
    return result


@component.adapter(IStreamChangeAcceptedByUser)
def user_mention_emailer(event):
    """
    For incoming changes containing mentions, email the user, assuming
    they're offline
    """

    user = event.target
    change = event.object
    mentionable = IMentionable(change.object, None)
    if      mentionable is not None \
        and _is_newly_mentioned(user, change):

        if not _is_subscribed_mentions(user):
            log_mention_notification(user, mentionable, change,
                                     skip_reason="user not subscribed")
            return

        log_mention_notification(user, mentionable, change)

        template_provider = IMailTemplateProvider(mentionable, None)
        template = template_provider.template if template_provider else 'mention_email'

        template_args = {}
        request = get_current_request()
        notable = _TemplateArgs((mentionable,),
                                request,
                                remoteUser=user,
                                max_snippet_len=250)
        template_args['notable'] = notable

        notable_context = get_top_level_context(mentionable)
        subject = _(u"%s mentioned you in %s" % (notable.creator, notable_context))

        # TODO: unsubscribe url for mentions
        # template_args['unsubscribe_link'] = generate_unsubscribe_url(request.remote_user, request)

        email = EmailAddresablePrincipal(user)
        template_args['email_to'] = '%s (%s)' % (email.email, email.id)
        template_args['display_name'] = _display_name(user, request)
        template_args['support_email'] = _support_email()
        template_args['notable_context'] = notable_context
        template_args['view'] = mentionable

        mailer = _mailer()
        mailer.queue_simple_html_text_email(
            template,
            package=push_pkg,
            subject=subject,
            recipients=[user],
            text_template_extension=".mak",
            template_args=template_args,
            request=request)


def log_mention_notification(user, mentionable, change, skip_reason=None):
    mentionable_oid = to_external_ntiid_oid(mentionable)
    logger.info("%s offline notification to %s for mention%s, "
                "chg: %s, object oid: %s",
                "Skipping" if skip_reason else "Sending",
                user.username,
                (" (%s)" % skip_reason) if skip_reason else "",
                change.type, mentionable_oid)
