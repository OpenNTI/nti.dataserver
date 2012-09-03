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
from pyramid_mailer.interfaces import IMailer


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
	# NOTE: The text refers to an attachment. Where is it and how are
	# we supposed to generate it?
	html_body = None
	text_body = render( 'templates/coppa_consent_request_email.txt',
						dict(user=user, profile=profile, context=user,master=master),
						request=event.request )

	message = Message( subject="COPPA Direct Notice", # TODO: i18n
					   recipients=[email],
					   body=text_body,
					   html=html_body )
	component.getUtility( IMailer ).send_to_queue( message )
