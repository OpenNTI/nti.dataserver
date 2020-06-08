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

from zope.intid.interfaces import IIntIds

from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate

from nti.app import pushnotifications as push_pkg

from nti.app.pushnotifications import email_notifications_preference

from nti.app.pushnotifications.digest_email import _TemplateArgs

from nti.app.pushnotifications.utils import get_top_level_context

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IStreamChangeAddedEvent

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


def _threadable_added(threadable, unused_event):
	inReplyTo = threadable.inReplyTo
	if not IThreadable.providedBy(inReplyTo):
		return

	if getattr(threadable, 'creator', None) == getattr(inReplyTo, 'creator', None):
		return

	user = User.get_user(getattr(inReplyTo, 'creator', None))
	if not _is_subscribed(user):
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
        return bool(dataserver.sessions.get_sessions_by_owner(username))
    except KeyError:  # Hmm. session_storage.py reports some inconsistency errors sometimes. Which is bad
        logger.exception("Failed to get all sessions for owner %s", username)
        return False


@component.adapter(IStreamChangeAddedEvent)
def user_mention_emailer(event):
    """
    For incoming changes containing mentions, email the user, assuming
    they're offline
    """

    user = event.target
    change = event.object
    mentionable = IMentionable(change.object, None)
    if mentionable is not None \
            and mentionable.isMentionedDirectly(user) \
            and not _is_user_online(user.username):
        logger.debug("Sending offline notification to %s for mention, chg: %s",
                     user.username, change.type)

        base_template = 'mention_email'

        template_args = {}
        request = get_current_request()
        notable = _TemplateArgs((change.object,),
                                request,
                                remoteUser=request.remote_user,
                                max_snippet_len=250)
        template_args['notable'] = notable

        notable_context = get_top_level_context(change.object)
        subject = "%s mentioned you in %s" % (notable.creator, notable_context)

        # TODO: unsubscribe url for mentions
        # template_args['unsubscribe_link'] = generate_unsubscribe_url(request.remote_user, request)

        email = EmailAddresablePrincipal(user)
        template_args['email_to'] = '%s (%s)' % (email.email, email.id)
        template_args['display_name'] = _display_name(user, request)
        template_args['support_email'] = _support_email()
        template_args['view'] = mentionable

        mailer = _mailer()
        mailer.queue_simple_html_text_email(
            base_template,
            package=push_pkg,
            subject=subject,
            recipients=[user],
            text_template_extension=".mak",
            template_args=template_args,
            request=request)
