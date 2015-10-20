#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nameparser import HumanName

from zope import component

from pyramid.view import view_defaults
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable

from .interfaces import IEmail

@view_defaults(route_name='objects.generic.traversal',
			   request_method='POST')
class AbstractMemberEmailView(AbstractAuthenticatedView,
							   ModeledContentUploadRequestUtilsMixin):

	inputClass = IEmail

	def predicate(self):
		"""
		Subclasses can override this to specify if the email is permitted.
		"""
		return True

	def reply_addr_for_recipient(self, recipient):
		"""
		Subclasses can override this to tailor the reply address
		by recipient.
		"""
		return self._no_reply_addr

	def readInput(self):
		email = super(AbstractMemberEmailView, self).readInput()
		# TODO Strip html?
		return email

	@property
	def _no_reply_addr(self):
		return 'no-reply@nextthought.com'

	def _email_address_for_user(self, user):
		addr = IEmailAddressable( user, None )
		return addr and addr.email

	def _get_user_first_name(self, user):
		named = IFriendlyNamed( user )
		human_name = None
		if named and named.realname:
			human_name = HumanName( named.realname )
		return human_name and human_name.first_name

	def get_template_args(self, user, body, to_addr):
		result = {}
		result['body'] = body
		result['email_to'] = to_addr
		result['first_name'] = self._get_user_first_name( user ) or to_addr
		return result

	def send_email(self, to_user, subject, body):
		reply_addr = self.reply_addr_for_recipient( to_user )
		to_addr = self._email_address_for_user( to_user )
		user_args = self.get_template_args( to_user, body, to_addr )
		try:
			# TODO package?
			mailer = component.getUtility(ITemplatedMailer)
			mailer.queue_simple_html_text_email(
								'member_email.pt',
								subject=subject,
								sender=reply_addr,
								recipients=[to_addr],
								template_args=user_args,
								request=self.request,
								text_template_extension=".mak" )
		except Exception:
			logger.exception('Error while sending email to %s', to_user)

	def __call__(self):
		if not self.predicate():
			raise hexc.HTTPForbidden()

		email = self.readInput()
		subject = email.Subject or self._default_subject()
		for member in self.iter_members():
			self.send_email( member, subject, email.body )
		return hexc.HTTPNoContent
