#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mailers that somehow filter their arguments before
actually creating or queuing mail.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from .interfaces import ITemplatedMailer

@interface.implementer(ITemplatedMailer)
class _BaseFilteredMailer(object):

	@property
	def _default_mailer(self):
		# We look up the utility by name, because we expect
		# to be registered in sub-sites to override the main utility
		return component.getUtility(ITemplatedMailer, name='default')

	def __getattr__(self, name):
		return getattr(self._default_mailer, name)


class NextThoughtOnlyMailer(_BaseFilteredMailer):
	"""
	This mailer ensures we only send email to nextthought.com
	addresses.
	"""

	def create_simple_html_text_email(self,
									  base_template,
									  subject='',
									  request=None,
									  recipients=(),
									  template_args=None,
									  attachments=(),
									  package=None,
									  text_template_extension='.txt'):
		# Implementation wise, we know that all activity
		# gets directed through this method, so we only need to filter
		# here.
		def _tx(addr):
			if addr.endswith('@nextthought.com'):
				return addr
			# XXX This blows up if we get a malformed
			# email address
			local, _ = addr.split('@')
			return 'dummy.email+' + local + '@nextthought.com'
		filtered_recip = [_tx(addr) for addr in recipients]

		return self._default_mailer.create_simple_html_text_email(base_template,
																  subject=subject,
																  request=request,
																  recipients=filtered_recip,
																  template_args=template_args,
																  attachments=attachments,
																  package=package,
																  text_template_extension=text_template_extension)
