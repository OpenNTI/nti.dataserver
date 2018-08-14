#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from pyramid.threadlocal import get_current_request

from zope import component

from zope.intid.interfaces import IIntIds

from zope.intid.interfaces import IIntIdAddedEvent

from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost

from nti.dataserver.interfaces import INote

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import EmailAddresablePrincipal

from nti.threadable.interfaces import IThreadable

from nti.app import pushnotifications as push_pkg

from nti.app.pushnotifications import email_notifications_preference

def _mailer():
	return component.getUtility(ITemplatedMailer)

def _is_subscribed(user):
	with email_notifications_preference(user) as prefs:
		return prefs.immediate_threadable_reply

@component.adapter(ICommentPost, IIntIdAddedEvent)
@component.adapter(INote, IIntIdAddedEvent)
def _threadable_added(threadable, event):
	inReplyTo = threadable.inReplyTo
	if not IThreadable.providedBy(inReplyTo):
		return

	if getattr(threadable, 'creator', None) == getattr(inReplyTo, 'creator', None):
		return

	user = User.get_user(getattr(inReplyTo, 'creator', None))
	if not _is_subscribed(user):
		return

	addr = IEmailAddressable(user, None)
	if not addr or not addr.email:
		return

	intids = component.getUtility(IIntIds)
	intid = intids.getId(threadable)
	recipient = {'email': EmailAddresablePrincipal(user),
				 'template_args': [intid],
				 'realname': IFriendlyNamed(user).realname,
				 'since': 0}

	request = get_current_request()

	delegate = component.getMultiAdapter((inReplyTo, request), IBulkEmailProcessDelegate, name="digest_email")
	subject = delegate.compute_subject_for_recipient(None)
	template_args = delegate.compute_template_args_for_recipient(recipient)
	template_args['notable_text'] = 'A user has replied to one of your comments.'

	# Currently we don't have a link for unsubscribing this email notification.
	template_args.pop('unsubscribe_link', None)

	text_template_extension=delegate.text_template_extension

	mailer = _mailer()
	mailer.queue_simple_html_text_email(delegate.template_name,
										subject=subject,
										recipients=[addr.email],
										template_args=template_args,
										reply_to=None,
										package=push_pkg,
										text_template_extension=text_template_extension)
