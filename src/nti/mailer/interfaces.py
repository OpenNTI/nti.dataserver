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

from zope import interface
from zope.security.interfaces import IPrincipal

from pyramid_mailer.interfaces import IMailer
IMailer = IMailer # re-export, primarily for testing

from repoze.sendmail.interfaces import IMailDelivery
IMailDelivery = IMailDelivery # re-export, primarily for testing

#pylint:disable=I0011,E0213

class IEmailAddressable(interface.Interface):
	"""
	Something containing an email address. Commonly, when
	the object containing the email address represents a \"user\"
	of the system, it should also be adaptable to :class:`zope.security.interfaces.IPrincipal`.

	See :class:`.EmailAddresablePrincipal` for a simple serialization-safe
	example.
	"""

	email = interface.Attribute("The email address to send to")

@interface.implementer(IEmailAddressable,
					   IPrincipal)
class EmailAddresablePrincipal(object):
	"""
	An implementation of both :class:`IEmailAddressable`
	and :class:`IPrincipal` that combines both interfaces
	from something (a context) that is adaptable to both. Use this
	when the weight of the context is undesirable, such as during
	serialization (pickling), or when concurrency is a factor.

	This object copies the attributes from both interfaces into
	itself at construction time.
	"""

	# These two attributes of IPrincipal aren't required
	title = None
	description = None

	def __init__(self, context):
		self.email = IEmailAddressable(context).email

		prin = IPrincipal(context)
		self.id = prin.id

		for name in 'title', 'description':
			prin_val = getattr(prin, name, None)
			if prin_val is not None:
				setattr(self, str(name), prin_val)

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
			from the list. Objects that are :class:`.IEmailAddressable` should also
			(optionally) be able to become :class:`zope.security.interfaces.IPrincipal`
			by adaptation; this may permit us to construct a better (e.g., VERP)
			message.

		:keyword text_template_extension: The filename extension for the plain text template. Valid
			values are ".txt" for Chameleon templates (this is the
			default and preferred version) and ".mak" for Mako
			templates. Note that if you use Mako, the usual
			``context`` argument is renamed to ``nti_context``, as
			``context`` is a reserved word in Mako (this may change in the future).
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

class IVERP(interface.Interface):
	"""
	Amazon SES now supports labels for `sending emails
	<http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html>`_,
	making it possible to do `VERP
	<https://en.wikipedia.org/wiki/Variable_envelope_return_path>`_,
	meaning we can directly identify the account we sent to (or even
	type of email) in case of a bounce This requires using 'labels'
	and modifying the sending address: foo+label@domain.com. Note that
	SES makes no mention of the Sender header, instead putting the
	labels directly in the From line (which is what, for example,
	Facebook does) or in the Return-Path line (which is what trello
	does). However, SES only deals with the Return-Path header if you
	use its `API, not if you use SMTP
	<http://docs.aws.amazon.com/ses/latest/DeveloperGuide/notifications-via-email.html>`_
	"""

	def verp_from_recipients(fromaddr, recipients, request=None):
		"""
		This function takes a given from address and manipulates it to
		include VERP information that identifies the *accounts* of the
		recipients. For this to work, the recipients must initially be
		passed as things that can be adapted to `IEmailAddressable`
		objects; for those objects that can be adapted, then if they can
		be adapted to :class:`.IPrincipal`, we include the principal ID.

		In addition, if the `fromaddr` does not include a realname,
		adds a default.

		.. note:: We take the request as an argument because at some point
			we may want to include some notion of the sending site,
			although it's probably better to use separate SES/SNS queues
			if possible.

		:param fromaddr: The initial from address, without any labels.

		:return: The ``fromaddr``, manipulated to include a VERP
			label, if possible, identifying the principals related to the
			recipients and/or request.
		"""

	def principal_ids_from_verp(fromaddr, request=None):
		"""
		Decode the VERP information as encoded in :meth:`verp_from_recipients`,
		returning a sequence of positively-identified principal IDs for the current
		environment, if any.
		"""
