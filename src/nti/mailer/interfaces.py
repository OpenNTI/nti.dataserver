#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""
Mailing interfaces.

This package is based upon both :mod:`pyramid_mailer` and :mod:`repoze.sendmail`,
but the relevant parts are re-exported from this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid_mailer.interfaces import IMailer
IMailer = IMailer # re-export, primarily for testing

from repoze.sendmail.interfaces import IMailDelivery
IMailDelivery = IMailDelivery # re-export, primarily for testing

class IEmailAddressable(interface.Interface):
	"""
	Something containing an email address.
	"""

	email = interface.Attribute("The email address to send to")

class ITemplatedMailer(interface.Interface):
	"""
	An object, typically registered as a utility,
	that can handle putting together an email (having both
	text and HTML parts) by rendering templates.
	"""

	def queue_simple_html_text_email(base_template,
									 subject='',
									 request=None,
									 recipients=(),
									 template_args=None,
									 attachments=(),
									 package=None,
									 text_template_extension='.txt'):
		"""
		Transactionally queues an email for sending. The email has both a
		plain text and an HTML version.

		:keyword recipients: A sequence of RFC822 email addresses as strings,
			or objects that can be adapted to an :class:`.IEmailAddressable`
			object. If no recipients are given, this does nothing. If any
			recipients are not strings, then if they cannot be adapted to
			:class:`.IEmailAddressable` or if the ``email`` attribute of the
			adapted object is false (none, empty) they will silently be dropped
			from the list.

		:keyword text_template_extension: The filename extension for the plain text template. Valid
			values are ".txt" for Chameleon templates (this is the
			default and preferred version) and ".mak" for Mako
			templates. Note that if you use Mako, the usual
			``context`` argument is renamed to ``nti_context``, as
			``context`` is a reserved word in Mako.
		:keyword package: If given, and the template is not an absolute
			asset spec, then the template will be interpreted relative to this
			package (and its templates/ subdirectory if no subdirectory is specified).
			If no package is given, the package of the caller of this function is used.

		:return: The :class:`pyramid_mailer.message.Message` we sent, if we sent one,
			otherwise None.
		"""

	def create_simple_html_text_email(base_template,
									  subject='',
									  request=None,
									  recipients=(),
									  template_args=None,
									  attachments=(),
									  package=None,
									  text_template_extension='.txt'):
		"""
		The same arguments and return types as :meth:`queue_simple_html_text_email`,
		but without the actual transactional delivery.
		"""

	def do_html_text_templates_exist(base_template,
									 text_template_extension='.txt',
									 package=None):
		"""
		A preflight method for checking if templates exist. Returns a True value
		if they do.
		"""
