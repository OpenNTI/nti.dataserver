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

from pyramid.threadlocal import get_current_request
from pyramid.renderers import render
from pyramid.renderers import get_renderer

from pyramid_mailer.interfaces import IMailer
from pyramid_mailer.message import Message
from repoze.sendmail import interfaces as mail_interfaces

def queue_simple_html_text_email(base_template, subject='', request=None, recipients=(), template_args=None):
	"""
	Transactionally queues an email for sending. The email has both a
	plain text and an HTML version
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

	master = get_renderer('templates/master_email.pt').implementation()
	def make_args():
		result = {}
		result['master'] = master
		if request:
			result['context'] = request.context
		if template_args:
			result.update( template_args )
		return result

	html_body, text_body = [render( 'templates/' + base_template + extension,
									make_args(),
									request=request )
							for extension in ('.pt', '.txt')]

	message = Message( subject=subject,
					   recipients=recipients,
					   body=text_body,
					   html=html_body )
	send_pyramid_mailer_mail( message )

def send_pyramid_mailer_mail( message ):
	"""
	Given a :class:`pyramid_mailer.message.Message`, transactionally deliver
	it to the queue.
	"""
	# The pyramid_mailer.Message class is slightly nicer than the
	# email package messages, if much less powerful. However, it makes the
	# mistake of using different methods for send vs send_to_queue.
	# It is built of top of repoze.sendmail and an IMailer contains two instances
	# of repoze.sendmail.interfaces.IMailDelivery, one for queue and one
	# for immediate, and those objects do the real work and also have a consistent
	# interfaces. It's easy to change the pyramid_mail message into a email message
	send_mail( pyramid_mail_message=message )

def send_mail( fromaddr=None, toaddrs=None, message=None, pyramid_mail_message=None ):
	"""
	Sends a message transactionally. The first three arguments are exactly the
	arguments that a :class:`repoze.sendmail.interfaces.IMailDelivery` takes; the
	fourth is a convenience argument for converting from pyramid_mailer. If
	the fromaddr is not given, it will default to the one configured for pyramid. If
	the destination address and message are not given, they will default to the ones
	provided in the pyramid_mail_message (which is required).
	"""

	pyramidmailer = component.queryUtility( IMailer )

	if fromaddr is None:
		fromaddr = getattr( pyramid_mail_message, 'sender', None ) or getattr( pyramidmailer, 'default_sender', None )

	if toaddrs is None:
		toaddrs = pyramid_mail_message.send_to # required

	if message is None:
		pyramid_mail_message.sender = fromaddr # required
		message = pyramid_mail_message.to_message()

	delivery = component.queryUtility( mail_interfaces.IMailDelivery ) or getattr( pyramidmailer, 'queue_delivery', None )
	if delivery:
		delivery.send( fromaddr, toaddrs, message )
	elif pyramidmailer and pyramid_mail_message:
		pyramidmailer.send_to_queue( pyramid_mail_message )
	else:
		raise RuntimeError( "No way to deliver message" )
