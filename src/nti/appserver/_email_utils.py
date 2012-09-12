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
	component.getUtility( IMailer ).send_to_queue( message )
