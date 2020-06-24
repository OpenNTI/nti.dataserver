#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.threadlocal import get_current_request

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

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

from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IStreamChangeAcceptedByUser

from nti.dataserver.users import User

from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import EmailAddresablePrincipal

from nti.threadable.interfaces import IThreadable


def _mailer():
	return component.getUtility(ITemplatedMailer)


def _is_subscribed(user):
	with email_notifications_preference(user) as prefs:
		return prefs.immediate_threadable_reply


def _display_name(user, request):
	return component.getMultiAdapter((user, request), IDisplayNameGenerator)()


def _is_mentioned(user, threadable):
    if not IMentionable.providedBy(threadable):
        return False

    return threadable.isMentionedDirectly(user)


def _threadable_added(threadable, unused_event):
	inReplyTo = threadable.inReplyTo
	if not IThreadable.providedBy(inReplyTo):
		return

	if getattr(threadable, 'creator', None) == getattr(inReplyTo, 'creator', None):
		return

	user = User.get_user(getattr(inReplyTo, 'creator', None))
	if not _is_subscribed(user) or _is_mentioned(user, threadable):
		return

	request = get_current_request()

	intids = component.getUtility(IIntIds)
	intid = intids.getId(threadable)
	recipient = {'email': EmailAddresablePrincipal(user),
				 'template_args': [intid],
				 'display_name': _display_name(user, request),
				 'since': 0}

	delegate = component.getMultiAdapter((inReplyTo, request),
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


def _display_name(user, request):
    return component.getMultiAdapter((user, request), IDisplayNameGenerator)()


def _support_email():
    policy = component.getUtility(ISitePolicyUserEventListener)
    support_email = getattr(policy, 'SUPPORT_EMAIL',
                            'support@nextthought.com')
    return support_email


def _is_user_online(username):
    dataserver = component.getUtility(IDataserver)
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
class UntitledMailTemplateProvider(_AbstractMailTemplateProvider):
    template_name = u"mention_email_untitled"


class _TemplateArgs(digest_email._TemplateArgs):

    @property
    def snippet(self):
        if not hasattr(self._primary, "body") \
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
    if mentionable is not None \
            and _is_newly_mentioned(user, change) \
            and not _is_user_online(user.username):
        logger.debug("Sending offline notification to %s for mention, chg: %s",
                     user.username, change.type)

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
