#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies based on the user. See also :mod:`nti.appserver.site_policies` for
site-based policies.
For content censoring policies based on the user, see :mod:`nti.appserver.censor_policies`.

This module is curently where preventing sharing for coppa kids is implemented.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import pkg_resources

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from zope.lifecycleevent import IObjectCreatedEvent
from zope.lifecycleevent import IObjectModifiedEvent

from . import httpexceptions as hexc

@component.adapter(nti_interfaces.IModeledContent, IObjectCreatedEvent)
def dispatch_content_created_to_user_policies( content, event ):
	component.handle( content, content.creator, event )

from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from nti.dataserver import users

@component.adapter(nti_interfaces.IModeledContent, IObjectModifiedEvent)
def dispatch_content_edited_to_user_policies( content, event ):
	editor = users.User.get_user( psec.authenticated_userid( get_current_request() ) )
	component.handle( content, editor, event )

@component.adapter(nti_interfaces.IModeledContent, nti_interfaces.ICoppaUserWithoutAgreement, IObjectCreatedEvent)
def veto_sharing_for_unsigned_coppa_create( content, creator, event ):
	if getattr( content, 'sharingTargets', None):
		raise hexc.HTTPForbidden( "Cannot share objects" )

@component.adapter(nti_interfaces.IModeledContent, nti_interfaces.ICoppaUserWithoutAgreement, IObjectModifiedEvent)
def veto_sharing_for_unsigned_coppa_edit( content, editor, event ):
	if getattr( content, 'sharingTargets', None ):
		raise hexc.HTTPForbidden( "Cannot share objects" )

@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class CoppaUserWithoutAgreementCapabilityFilter(object):
	"""
	This policy filters out things that users that are probably kids and
	subject to COPPA cannot do.
	"""

	def __init__( self, context=None ):
		pass

	def filterCapabilities( self, capabilities ):
		return set()

from pyramid.renderers import render
from pyramid.renderers import get_renderer
from pyramid_mailer.message import Message
from pyramid_mailer.message import Attachment
from pyramid_mailer.interfaces import IMailer
from email.mime.application import MIMEApplication


@component.adapter(nti_interfaces.IUser, app_interfaces.IUserCreatedWithRequestEvent)
def send_email_on_new_account( user, event ):
	"""
	For new accounts where we have an email (and of course the request), we send a welcome message.

	Notice that we do not have an email collected for the ICoppaUserWithoutAgreement, so
	they will never get a notice here. (And we don't have to specifically check for that).
	"""

	if not event.request: #pragma: no cover
		return

	profile = user_interfaces.IUserProfile( user )
	email = getattr( profile, 'email' )
	if not email:
		return

	# Need to send both HTML and plain text if we send HTML, because
	# many clients still do not render HTML emails well (e.g., the popup notification on iOS
	# only works with a text part)
	master = get_renderer('templates/master_email.pt').implementation()
	html_body = render( 'templates/new_user_created.pt',
						dict(user=user, profile=profile, context=user,master=master),
						request=event.request )
	text_body = render( 'templates/new_user_created.txt',
						dict(user=user, profile=profile, context=user,master=master),
						request=event.request )

	message = Message( subject="Welcome to NextThought", # TODO: i18n
					   recipients=[email],
					   body=text_body,
					   html=html_body )
	component.getUtility( IMailer ).send_to_queue( message )

@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement, app_interfaces.IUserCreatedWithRequestEvent)
def send_consent_request_on_new_coppa_account( user, event ):
	"""
	For new accounts where we have an contact email (and of course the request),
	we send a consent request.

	"""

	if not event.request: #pragma: no cover
		return


	profile = user_interfaces.IUserProfile( user )
	email = getattr( profile, 'contact_email' )
	if not email:
		return

	# Need to send both HTML and plain text if we send HTML, because
	# many clients still do not render HTML emails well (e.g., the popup notification on iOS
	# only works with a text part)
	master = get_renderer('templates/master_email.pt').implementation()
	html_body = render( 'templates/coppa_consent_request_email.pt',
						dict(user=user, profile=profile, context=user,master=master),
						request=event.request )
	text_body = render( 'templates/coppa_consent_request_email.txt',
						dict(user=user, profile=profile, context=user,master=master),
						request=event.request )

	# TODO: It would be nice if this PDF was prefilled with some fields
	attachment_filename = 'coppa_consent_request_email_attachment.pdf'
	attachment = pkg_resources.resource_stream( 'nti.appserver.templates',
												attachment_filename )
	# There are problems using the released version attachments:
	#https://github.com/Pylons/pyramid_mailer/issues/18
	# So the workaround is to use the email package directly:
	attachment = MIMEApplication(attachment.read(), 'pdf' )
	attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)

	message = Message( subject="Please Confirm Your Child's NextThought Account", # TODO: i18n
					   recipients=[email],
					   sender='no-reply@nextthought.com', # The default, but explicitly needed for the attachment handling below
					   body=None,
					   html=html_body)

	# (Add this to ensure we get a multipart message - it will be removed later)
	message.attach(Attachment('foo.txt', 'text/plain', 'foo'))


	msg = message.to_message()
	msg.set_payload([p for p in msg.get_payload() if p.get_filename() != 'foo.txt'] + [attachment])
	# The problem with this is that we wind up with a multipart/alternative if we
	# send the text, html, and pdf, which makes it very hard to get to the PDF.
	# We need to send multipart/mixed. But if we do that with all three types, they all three wind
	# up displayed, which is not what we want either since two are alternatives
	# We must be doing something wrong
	#msg.set_type( 'multipart/mixed' )
	mailer = component.getUtility( IMailer )
	if getattr( mailer, 'queue_delivery', None) is not None:
		mailer.queue_delivery.send(message.sender, message.send_to, msg)
	else:
		#tests
		message.body = text_body
		mailer.send_to_queue( message )

	# We can log that we sent the message to the contact person for operational purposes,
	# but we cannot preserve it
	logger.info( "Will send COPPA consent notice to %s on behalf of %s", email, user.username )

	setattr( profile, 'contact_email', None )
