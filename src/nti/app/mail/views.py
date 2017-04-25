#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import hashlib

from nameparser import HumanName

from zope import component

from zope.cachedescriptors.property import Lazy

from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.mail.interfaces import IEmail

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.common.string import is_true

from nti.contentfragments.html import sanitize_user_html

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.users.interfaces import IAvatarURL
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable

AVATAR_BG_COLORS = ["#5E35B1", "#3949AB", "#1E88E5", "#039BE5",
					"#00ACC1", "#00897B", "#43A047", "#7CB342",
					"#C0CA33", "#FDD835", "#FFB300", "#FB8C00", "#F4511E"]

class AbstractMemberEmailView(AbstractAuthenticatedView,
							  ModeledContentUploadRequestUtilsMixin):
	"""
	An abstract view used to email one or members of an entity. The
	``iter_members`` function defines which members are emailed.
	Subclasses may also define ``predicate`` or ``reply_addr_for_recipient``
	to define specific member email behavior.

	This view accepts an ``IEmail`` body, of which the body
	may be fully formed HTML.
	"""

	#: By default, we only email to internal users
	EMAIL_EXTERNALLY_DEFAULT = False

	@property
	def _no_reply_addr(self):
		return 'no-reply@nextthought.com'

	@Lazy
	def _sender_reply_addr(self):
		result = self._email_address_for_user(self.sender)
		return result or self._no_reply_addr

	@property
	def sender(self):
		return self.remoteUser

	@Lazy
	def support_email(self):
		policy = component.getUtility(ISitePolicyUserEventListener)
		support_email = getattr(policy, 'SUPPORT_EMAIL', 'support@nextthought.com')
		return support_email

	@Lazy
	def sender_avatar_url(self):
		avatar_container = IAvatarURL(self.sender)
		if avatar_container.avatarURL:
			return self.request.resource_url(self.sender, '@@avatar')
		return None

	@Lazy
	def sender_avatar_initials(self):
		# XXX: Logic copied from digest_email.py
		named = IFriendlyNamed(self.sender)
		human_name = None
		if named and named.realname:
			human_name = HumanName(named.realname)
		# User's initials if we have both first and last
		if human_name and human_name.first and human_name.last:
			result = human_name.first[0] + human_name.last[0]
		# Or the first initial of alias/real/username
		else:
			named = named.alias or named.realname or self.sender.username
			result = named[0]
		return result

	@Lazy
	def sender_avatar_bg_color(self):
		# Hash the username into our BG color array.
		username = self.sender.username
		username_hash = hashlib.md5(username.lower()).hexdigest()
		username_hash = int(username_hash, 16)
		index = username_hash % len(AVATAR_BG_COLORS)
		result = AVATAR_BG_COLORS[ index ]
		return result

	@Lazy
	def sender_display_name(self):
		names = IFriendlyNamed(self.sender)
		return names.alias or names.realname or self.sender.username

	@Lazy
	def email_externally(self):
		settings = component.getUtility(IApplicationSettings)
		val = settings.get('email_externally',
							self.EMAIL_EXTERNALLY_DEFAULT)
		return is_true(val)

	def __accept_user(self, user):
		# Only email externally if configured to do so. Otherwise, only
		# email NT users.
		# TODO: We have NextThoughtOnlyMailer as well, but we want to
		# *not* email externally when on TEST sites (like we do with
		# the test endpoint for notables). It would be nice to unify
		# this logic somewhere. Perhaps we never email externally
		# except in production envs.
		# TODO: Only verified emails?
		if not self.email_externally:
			email = getattr(IEmailAddressable(user, None), 'email', None)
			return 	email	\
				and (	email == 'jamadden@ou.edu' \
					or	email == 'jzuech3@gmail.com' \
					or 	email.endswith('@nextthought.com'))
		return True

	@property
	def _context_display_name(self):
		"""
		Subclasses should implement this to define a context
		display name property in the email template.
		"""
		raise NotImplementedError()

	@property
	def _context_logged_info(self):
		"""
		Subclasses should implement this to log context.
		"""
		return ''

	def _default_subject(self):
		"""
		Subclasses should implement this to define a default subject
		if none is provided.
		"""
		raise NotImplementedError()

	def predicate(self):
		"""
		Subclasses can override this to specify if the email is permitted.
		"""
		return True

	def reply_addr_for_recipient(self, unused_recipient):
		"""
		Subclasses can override this to tailor the reply address
		by recipient.
		"""
		return self._no_reply_addr

	def iter_members(self):
		"""
		Subclasses must override this to define the members who will
		receive an email.
		"""
		raise NotImplementedError()

	def readInput(self):
		email_json = super(AbstractMemberEmailView, self).readInput()
		mail_obj = find_factory_for(email_json)()
		update_from_external_object(mail_obj, email_json)
		if not IEmail.providedBy(mail_obj):
			raise hexc.HTTPUnprocessableEntity()
		return mail_obj

	def _email_address_for_user(self, user):
		addr = IEmailAddressable(user, None)
		return addr and addr.email

	def get_template_args(self, body, to_addr):
		result = {}
		result['body'] = body
		result['text_body'] = IPlainTextContentFragment(body)
		result['email_to'] = to_addr
		result['support_email'] = self.support_email
		result['sender_name'] = self.sender_display_name
		result['sender_avatar_url'] = self.sender_avatar_url
		result['sender_avatar_initials'] = self.sender_avatar_initials
		result['sender_avatar_bg_color'] = self.sender_avatar_bg_color
		result['context_display_name'] = self._context_display_name
		return result

	def _get_body(self, email):
		# Make sure we sanitize our user input
		body = sanitize_user_html(email.Body)
		return body

	def _get_reply_addr(self, to_user, email):
		if email.NoReply:
			result = self._no_reply_addr
		else:
			result = self.reply_addr_for_recipient(to_user)
		return result

	def send_email(self, to_user, subject, body, email):
		reply_addr = self._get_reply_addr(to_user, email)
		to_addr = self._email_address_for_user(to_user)
		user_args = self.get_template_args(body, to_addr)
		try:
			mailer = component.getUtility(ITemplatedMailer)
			mailer.queue_simple_html_text_email(
								'member_email',
								subject=subject,
								reply_to=reply_addr,
								recipients=[to_addr],
								template_args=user_args,
								request=self.request,
								text_template_extension=".mak")
		except Exception:
			logger.exception('Error while sending email to %s', to_user)

	def __call__(self):
		if not self.predicate():
			raise hexc.HTTPForbidden()

		email = self.readInput()
		subject = email.Subject or self._default_subject()
		body = self._get_body(email)
		send_count = 0

		for member in self.iter_members():
			if self.__accept_user(member):
				send_count += 1
				self.send_email(member, subject, body, email)

		# Now copy to author
		if email.Copy and self.__accept_user(self.sender):
			logger.info( 'Sending email copy to %s (%s)',
						 self.sender, self._sender_reply_addr)
			subject = '[COPY] %s' % subject
			self.send_email(self.sender, subject, body, email)

		logger.info('%s sent %s emails to %s (NoReply=%s) (sender_reply=%s) (copy_sender=%s)',
					self.remoteUser, send_count, self._context_logged_info,
					email.NoReply, self._sender_reply_addr, email.Copy)
		return hexc.HTTPNoContent()
