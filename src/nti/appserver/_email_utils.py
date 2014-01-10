#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions having to do with sending emails.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.dottedname import resolve as dottedname

from pyramid.renderers import render
from pyramid.renderers import get_renderer
from pyramid.path import caller_package
from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Message
from pyramid_mailer.interfaces import IMailer
from pyramid_mailer.message import Attachment

from repoze.sendmail import interfaces as mail_interfaces

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
								 package=None):
	"""
	A preflight method for checking if templates exist. Returns a True value
	if they do.
	"""
	try:
		_get_renderer( base_template, '.pt', package=package )
		_get_renderer( base_template, text_template_extension, package=package )
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
	kwargs['_level'] = 4
	return send_pyramid_mailer_mail( create_simple_html_text_email( *args, **kwargs ) )

def send_pyramid_mailer_mail( message ):
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
	send_mail( pyramid_mail_message=message )
	return message

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

def send_mail( fromaddr=None, toaddrs=None, message=None, pyramid_mail_message=None ):
	"""
	Sends a message transactionally. The first three arguments are exactly the
	arguments that a :class:`repoze.sendmail.interfaces.IMailDelivery` takes; the
	fourth is a convenience argument for converting from :mod:`pyramid_mailer`. If
	the ``fromaddr`` is not given, it will default to the one configured for pyramid. If
	the destination address and message are not given, they will default to the ones
	provided in the ``pyramid_mail_message`` (which is required).
	"""
	assert pyramid_mail_message is not None
	pyramidmailer = component.queryUtility( IMailer )

	if fromaddr is None:
		fromaddr = getattr( pyramid_mail_message, 'sender', None )
	if not fromaddr:
		# Can we get a site policy for the current site?
		# It would be the unnamed IComponents
		policy = component.queryUtility(ISitePolicyUserEventListener)
		if policy:
			fromaddr = getattr(policy, 'DEFAULT_EMAIL_SENDER', None)
	if not fromaddr:
		fromaddr = getattr( pyramidmailer, 'default_sender', None )

	if toaddrs is None:
		toaddrs = pyramid_mail_message.send_to # required

	if message is None:
		pyramid_mail_message.sender = fromaddr # required
		message = pyramid_mail_message.to_message()

	delivery = component.queryUtility( mail_interfaces.IMailDelivery ) or getattr( pyramidmailer, 'queue_delivery', None )
	if delivery:
		__traceback_info__ = fromaddr, toaddrs
		delivery.send( fromaddr, toaddrs, message )
	elif pyramidmailer and pyramid_mail_message:
		pyramidmailer.send_to_queue( pyramid_mail_message )
	else:
		raise RuntimeError( "No way to deliver message" )
