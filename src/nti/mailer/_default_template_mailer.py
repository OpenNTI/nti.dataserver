#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions having to do with sending emails.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import rfc822

from zope import component
from zope import interface

from zope.dottedname import resolve as dottedname

from pyramid.renderers import render
from pyramid.renderers import get_renderer
from pyramid.path import caller_package
from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Message

from .interfaces import IMailer
from .interfaces import IMailDelivery
from .interfaces import ITemplatedMailer
from .interfaces import IEmailAddressable
from zope.security.interfaces import IPrincipal

from six import string_types

def _get_renderer_spec_and_package(base_template,
								   extension,
								   package=None,
								   level=3):
	if isinstance(package,basestring):
		package = dottedname.resolve(package)

	# Did they give us a package, either in the name or as an argument?
	# If not, we need to get the right package
	if ':' not in base_template and package is None:
		package = caller_package(level) # 2 would be our caller, aka this module.
	# Do we need to look in a subdirectory?
	if ':' not in base_template and '/' not in base_template:
		base_template = 'templates/' + base_template

	# pyramid_mako does not properly accept a package argument
	# and a relative template path; such a specification is
	# considered to be relative to mako's search directory,
	# which is not what we want. We could fix this with a special
	# TemplateLookup object, but instead it's a quick
	# hack to alter the names here
	if extension == '.mak' and ':' not in base_template:
		base_template = package.__name__ + ':' + base_template

	return base_template + extension, package


def _get_renderer(base_template,
				  extension,
				  package=None,
				  level=3):
	"""
	Given a template name, find a renderer for it.
	For template name, we accept either a relative or absolute
	asset spec. If the spec is relative, it can be 'naked', in which
	case it is assummed to be in the templates sub directory.

	This *must* only be called from this module due to assumptions
	about the call tree.
	"""

	template, package = _get_renderer_spec_and_package( base_template,
														extension,
														package=package,
														level=level+1 )

	return get_renderer( template, package=package )

def do_html_text_templates_exist(base_template,
								 text_template_extension='.txt',
								 package=None,
								 _level=3):
	"""
	A preflight method for checking if templates exist. Returns a True value
	if they do.
	"""
	try:
		_get_renderer( base_template, '.pt', package=package, level=_level )
		_get_renderer( base_template, text_template_extension, package=package, level=_level )
	except ValueError:
		# Pyramid raises this if the template doesn't exist
		return False
	return True

def create_simple_html_text_email(base_template,
								  subject='',
								  request=None,
								  recipients=(),
								  template_args=None,
								  attachments=(),
								  package=None,
								  text_template_extension='.txt',
								  _level=3):
	"""
	Create a :class:`pyramid_mailer.message.Message` by rendering
	the pair of templates to create a text and html part.

	:keyword text_template_extension: The filename extension for the plain text template. Valid values
		are ".txt" for Chameleon templates (this is the default and preferred version) and ".mak" for
		Mako templates. Note that if you use Mako, the usual ``context`` argument is renamed to ``nti_context``,
		as ``context`` is a reserved word in Mako.
	:keyword package: If given, and the template is not an absolute
		asset spec, then the template will be interpreted relative to this
		package (and its templates/ subdirectory if no subdirectory is specified).
		If no package is given, the package of the caller of this function is used.
	"""

	if recipients:
		# Convert any IEmailAddressable into their email, and strip
		# empty strings
		recipients = [getattr(IEmailAddressable(x,x), 'email', x)
					  for x in recipients]
		recipients = [x for x in recipients if isinstance(x, string_types) and x]

	if not recipients:
		logger.debug( "Refusing to attempt to send email with no recipients" )
		return
	if not subject:
		# TODO: Should the subject already be localized or should we do that?
		logger.debug( "Refusing to attempt to send email with no subject" )
		return

	if request is None:
		request = get_current_request()

	def make_args(extension):
		# Mako gets bitchy if 'context' comes in as an argument, but
		# that's what Chameleon wants. To simplify things, we handle that
		# for our callers. They just want to use 'context'
		the_context_name = 'nti_context' if extension == text_template_extension and text_template_extension != '.txt' else 'context'
		result = {}
		if request:
			result[the_context_name] = request.context
		if template_args:
			result.update( template_args )

		if the_context_name == 'nti_context' and 'context' in template_args:
			result[the_context_name] = template_args['context']
			del result['context']
		return result

	specs_and_packages = [_get_renderer_spec_and_package( base_template,
														  extension,
														  package=package,
														  level=_level) + (extension,)
							for extension in ('.pt', text_template_extension)]

	html_body, text_body = [render( spec,
									make_args(extension),
									request=request,
									package=package)
							for spec, package, extension in specs_and_packages]
	# PageTemplates (Chameleon and Z3c.pt) produce Unicode strings.
	# Under python2, at least, the text templates (Chameleon alone) produces byte objects,
	# (JAM: TODO: Can we make it stay in the unicode realm? Pyramid config?)
	# (JAM: TODO: Not sure about what Mako does?)
	# apparently encoded as UTF-8, which is not ideal. This either is
	# a bug itself (we shouldn't pass non-ascii values as text/plain)
	# or triggers a bug in pyramid mailer when it tries to figure out the encoding,
	# leading to a UnicodeError.
	# The fix is to supply the charset parameter we want to encode as;
	# Or we could decode it ourself, which lets us use the optimal encoding
	# pyramid_mailer picks...we ignore errors
	# here to make sure that we can send /something/
	if isinstance(text_body, bytes):
		text_body = text_body.decode('utf-8', 'replace')

	# JAM: Why are we quoted-printable encoding? That produces much bigger
	# output...whether we do it like this, or simply pass in the unicode
	# strings, we get quoted-printable. We would pass Attachments if we
	# wanted to specify the charset (see above)
	#message = Message( subject=subject,
	#				   recipients=recipients,
	#				   body=Attachment(data=text_body, disposition='inline',
	#								   content_type='text/plain',
	#								   transfer_encoding='quoted-printable'),
	#				   html=Attachment(data=html_body, disposition='inline',
	#								   content_type='text/html',
	#								   transfer_encoding='quoted-printable') )
	message = Message( subject=subject,
					   recipients=recipients,
					   body=text_body,
					   html=html_body,
					   attachments=attachments )

	return message


def queue_simple_html_text_email(*args, **kwargs):
	"""
	Transactionally queues an email for sending. The email has both a
	plain text and an HTML version.

	:keyword text_template_extension: The filename extension for the plain text template. Valid values
		are ".txt" for Chameleon templates (this is the default and preferred version) and ".mak" for
		Mako templates. Note that if you use Mako, the usual ``context`` argument is renamed to ``nti_context``,
		as ``context`` is a reserved word in Mako.

	:return: The :class:`pyramid_mailer.message.Message` we sent.
	"""

	kwargs = dict(kwargs)
	if '_level' not in kwargs:
		kwargs['_level'] = 4
	return _send_pyramid_mailer_mail( create_simple_html_text_email( *args, **kwargs ),
									  recipients=kwargs.get('recipients'),
									  request=kwargs.get('request'))

def _send_pyramid_mailer_mail( message, recipients=None, request=None ):
	"""
	Given a :class:`pyramid_mailer.message.Message`, transactionally deliver
	it to the queue.

	:return: The :class:`pyramid_mailer.message.Message` we sent.
	"""
	# The pyramid_mailer.Message class is slightly nicer than the
	# email package messages, if much less powerful. However, it makes the
	# mistake of using different methods for send vs send_to_queue.
	# It is built of top of repoze.sendmail and an IMailer contains two instances
	# of repoze.sendmail.interfaces.IMailDelivery, one for queue and one
	# for immediate, and those objects do the real work and also have a consistent
	# interfaces. It's easy to change the pyramid_mail message into a email message
	_send_mail( pyramid_mail_message=message, recipients=recipients, request=request )
	return message

# TODO: Break these dependencies
from nti.appserver.policies.interfaces import ISitePolicyUserEventListener
from nti.appserver.interfaces import IApplicationSettings

import itsdangerous

def _make_signer(default_key='$Id$'):
	settings = component.getGlobalSiteManager().queryUtility(IApplicationSettings) or {}
	# XXX Reusing the cookie secret, we should probably have our own
	secret_key = settings.get('cookie_secret', default_key)

	signer = itsdangerous.Signer(secret_key, salt='email recipient')
	return signer

def _compute_from( fromaddr, recipients, request ):
	"""
	Amazon SES now supports labels for `sending emails
	<http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html>`_`,
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

	This function takes a given from address and manipulates it to
	include VERP information that identifies the *accounts* of the
	recipients. For this to work, the recipients must initially be
	passed as things that can be adapted to `IEmailAddressable`
	objects; for those objects that can be adapted, then if they can
	be adapted to :class:`.IPrincipal`, we include the principal ID.

	In addition, if the `fromaddr` does not include a realname,
	adds a default.

	A variation of this function will eventually be made public, as will a version
	that decodes.

	.. note:: We take the request as an argument because at some point
		we may want to include some notion of the sending site,
		although it's probably better to use separate SES/SNS queues
		if possible.
	"""

	realname, addr = rfc822.parseaddr(fromaddr)
	if not realname and not addr:
		raise ValueError("Invalid fromaddr", fromaddr)
	if '+' in addr:
		raise ValueError("Addr should not already have a label", fromaddr)

	if not realname:
		realname = "NextThought" # XXX Site specific?


	# We could special case the common case of recpients of length
	# one if it is a string: that typically means we're sending to the current
	# principal (though not necessarily so we'd have to check email match).
	# However, instead, I just want to change everything to send something
	# adaptable to IEmailAddressable instead.

	adaptable_to_email_addressable = [x for x in recipients
									  if IEmailAddressable(x,None) is not None]
	principals = {IPrincipal(x, None) for x in adaptable_to_email_addressable}
	principals.discard(None)

	principal_ids = {x.id for x in principals}
	if principal_ids:
		principal_ids = ','.join(principal_ids)
		# mildly encode them; this is just obfuscation.
		# Do that after signing to be sure we wind up with
		# something rfc822-safe
		# First, get bytes to avoid any default-encoding
		principal_ids = principal_ids.encode('utf-8')
		# now sign
		signer = _make_signer()
		principal_ids = signer.sign(principal_ids)
		# finally obfuscate in a url/email safe way
		principal_ids = itsdangerous.base64_encode(principal_ids)

		local, domain = addr.split('@')
		addr = local + '+' + principal_ids + '@' + domain

	return rfc822.dump_address_pair( (realname, addr) )

def _principal_ids_from_addr(fromaddr, default_key=None):
	if not fromaddr or '+' not in fromaddr:
		return ()

	_, addr = rfc822.parseaddr(fromaddr)
	if '+' not in addr:
		return ()

	signed_and_encoded = addr.split('+', 1)[1].split('@')[0]
	signed_and_decoded = itsdangerous.base64_decode(signed_and_encoded)

	signer = _make_signer() if not default_key else _make_signer(default_key=default_key)
	try:
		pids = signer.unsign(signed_and_decoded)
	except itsdangerous.BadSignature:
		return ()
	else:
		return pids.split(',')

def _pyramid_message_to_message( pyramid_mail_message, recipients, request ):
	"""
	Preps a pyramid message for sending, including adjusting its sender if needed.

	:return:
	"""
	assert pyramid_mail_message is not None
	pyramidmailer = component.queryUtility( IMailer )
	if request is None:
		request = get_current_request()


	fromaddr = getattr( pyramid_mail_message, 'sender', None )
	if not fromaddr:
		# Can we get a site policy for the current site?
		# It would be the unnamed IComponents
		policy = component.queryUtility(ISitePolicyUserEventListener)
		if policy:
			fromaddr = getattr(policy, 'DEFAULT_EMAIL_SENDER', None)
	if not fromaddr:
		fromaddr = getattr( pyramidmailer, 'default_sender', None )

	if not fromaddr:
		raise RuntimeError("No one to send mail from")

	fromaddr = _compute_from(fromaddr, recipients, request)

	pyramid_mail_message.sender = fromaddr # required
	message = pyramid_mail_message.to_message()
	return message


def _send_mail( pyramid_mail_message=None, recipients=(), request=None ):
	"""
	Sends a message transactionally.
	"""
	assert pyramid_mail_message is not None
	pyramidmailer = component.queryUtility( IMailer )

	message = _pyramid_message_to_message(pyramid_mail_message, recipients, request)

	delivery = component.queryUtility( IMailDelivery ) or getattr( pyramidmailer, 'queue_delivery', None )
	if delivery:
		delivery.send( pyramid_mail_message.sender,
					   pyramid_mail_message.send_to,
					   message )
	elif pyramidmailer and pyramid_mail_message:
		pyramidmailer.send_to_queue( pyramid_mail_message )
	else:
		raise RuntimeError( "No way to deliver message" )

interface.moduleProvides(ITemplatedMailer)
