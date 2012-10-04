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
from nti.appserver import MessageFactory as _
import pkg_resources

from zope import component
from zope import interface
from zope.schema import interfaces as sch_interfaces
import dolmen.builtins

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from pyramid import interfaces as pyramid_interfaces

from zope.lifecycleevent import IObjectCreatedEvent
from zope.lifecycleevent import IObjectModifiedEvent
from zope.annotation.interfaces import IAnnotations

from . import httpexceptions as hexc
from . import _email_utils
from ._util import link_belongs_to_user

from nti.dataserver.links import Link

@component.adapter(nti_interfaces.IModeledContent, IObjectCreatedEvent)
def dispatch_content_created_to_user_policies( content, event ):
	component.handle( content, content.creator, event )

from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from nti.dataserver import users
from nti.dataserver.users import user_profile

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

#: This relationship is exposed on Users and in the handshake/ping
#: when the UI should display it as a link to information about
#: our "Children's Privacy Policy."
REL_CHILDRENS_PRIVACY = 'childrens-privacy'

#: The relationship that is exposed when editing a user's profile's
#: ``contact_email`` field will result in sending a COPPA consent
#: request email to the new address. The link value itself turns
#: out to be the address of the ``contact_email`` field, so an application
#: can simply PUT to the value of this link to trigger sending the email.
#:
#: .. note::
#:     There may be rate limits and other restrictions on the
#:     ``contact_email``, so be prepared to handle errors when
#:     editing this value.
#:
REL_CONTACT_EMAIL_SENDS_CONSENT = 'contact-email-sends-consent-request'

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.ICoppaUser,pyramid_interfaces.IRequest)
class CoppaUserPrivacyPolicyLinkProvider(object):

	def __init__( self, user=None, request=None ):
		self.user = user

	def get_links( self ):
		link = Link( 'https://docs.google.com/document/pub?id=1kNo6hwwKwWdhq7jzczAysUWhnsP9RfckIet11pWPW6k',
					  rel=REL_CHILDRENS_PRIVACY,
					  target_mime_type='text/html' )
		link_belongs_to_user( link, self.user )
		return (link,)

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement,pyramid_interfaces.IRequest)
class CoppaUserWithoutAgreementContactEmailLinkProvider(object):

	def __init__( self, user=None, request=None ):
		self.user = user

	def get_links( self ):
		link = Link( self.user,
					 rel=REL_CONTACT_EMAIL_SENDS_CONSENT,
					 elements=( '++fields++contact_email', ) )
		link_belongs_to_user( link, self.user )
		return (link,)


from pyramid.renderers import render
from pyramid.renderers import get_renderer
from pyramid_mailer.message import Message
from pyramid_mailer.message import Attachment
from email.mime.application import MIMEApplication


CONTACT_EMAIL_RECOVERY_ANNOTATION = __name__ + '.contact_email_recovery_hash'

@component.adapter(nti_interfaces.ICoppaUser,app_interfaces.IUserUpgradedEvent)
def send_consent_ack_email(user, event):
	"""
	If we're upgrading a user from non-approved to approved, and we have a contact email,
	send the approval to the parent.
	"""

	if getattr( event.upgraded_profile, 'contact_email', None ):
		_email_utils.queue_simple_html_text_email( 'coppa_consent_approval_email',
												   subject=_("NextThought Account Confirmation"),
												   recipients=[event.upgraded_profile.contact_email],
												   template_args={'user': user, 'profile': event.upgraded_profile, 'context': user },
												   request=event.request )


@component.adapter(dolmen.builtins.IUnicode, user_interfaces.IRestrictedUserProfileWithContactEmail, sch_interfaces.IBeforeObjectAssignedEvent)
def send_consent_request_when_contact_email_changes( new_email, profile, event ):
	"""
	When users that are still pending an agreement change their contact email, we need to fire a consent
	request.

	Note that some types of users still have a contact_email, but they do not use an IRestrictedUserProfileWithContactEmail
	(specifically the IMathcountsCoppaUserWithAgreement), so they will never get here.
	"""

	if 'contact_email' != event.name:
		return # Note: We get two of these, one from the interface, one from the FieldPropertyStoredTHroughField named '__st_contact_email_st'

	user = profile.__parent__
	if not nti_interfaces.ICoppaUserWithoutAgreement.providedBy( user ) or not getattr( user, '_p_mtime', None ):
		# Do not do this if it's not in need of agreement.
		# also do not do this when the user is initially being created.
		return


	if new_email == profile.contact_email:
		# Ordinarily this won't be the case because we clear out the contact_email from
		# the profile when we send. But belt and suspenders.
		return

	event.request = get_current_request()
	_send_consent_request( user, profile, new_email, event )
	event.object = None # Got to prohibit actually storing this.



@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement, app_interfaces.IUserCreatedWithRequestEvent)
def send_consent_request_on_new_coppa_account( user, event ):
	"""
	For new accounts where we have an contact email (and of course the request),
	we send a consent request.

	"""
	profile = user_interfaces.IUserProfile( user )
	email = getattr( profile, 'contact_email' )
	_send_consent_request( user, profile, email, event )

def _send_consent_request( user, profile, email, event ):

	if not email:
		return

	if not event.request: #pragma: no cover
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

	attachment_filename = 'coppa_consent_request_email_attachment.pdf'
	attachment = pkg_resources.resource_stream( 'nti.appserver.templates',
												attachment_filename )
	# Prefill the fields.
	attachment = _alter_pdf( attachment, user.username, profile.realname, email )
	# There are problems using the released version attachments:
	#https://github.com/Pylons/pyramid_mailer/issues/18
	# So the workaround is to use the email package directly:
	attachment = MIMEApplication(attachment.read(), 'pdf' )
	attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)

	message = Message( subject=_("Please Confirm Your Child's NextThought Account"),
					   recipients=[email],
					   sender='no-reply@nextthought.com', # The default, but explicitly needed for the attachment handling below
					   body=None,
					   html=html_body)

	# (Add this to ensure we get a multipart message - it will be removed later)
	message.attach(Attachment('foo.txt', 'text/plain', 'foo'))


	email_msg = message.to_message()
	email_msg.set_payload([p for p in email_msg.get_payload() if p.get_filename() != 'foo.txt'] + [attachment])
	# The problem with this is that we wind up with a multipart/alternative if we
	# send the text, html, and pdf, which makes it very hard to get to the PDF.
	# We need to send multipart/mixed. But if we do that with all three types, they all three wind
	# up displayed, which is not what we want either since two are alternatives
	# We must be doing something wrong
	#email_msg.set_type( 'multipart/mixed' )
	message.body = text_body # mainly tests
	_email_utils.send_mail( message=email_msg, pyramid_mail_message=message )

	# We can log that we sent the message to the contact person for operational purposes,
	# but we cannot preserve it
	logger.info( "Will send COPPA consent notice to %s on behalf of %s", email, user.username )
	setattr( profile, 'contact_email', None )

	# We do need to keep something machine readable, though, for purposes of bounces
	# The cheap way to do it is with annotations
	IAnnotations( user )[CONTACT_EMAIL_RECOVERY_ANNOTATION] = user_profile.make_password_recovery_email_hash( email )

import pyPdf
import pyPdf.generic
from cStringIO import StringIO

def _alter_pdf( pdf_stream, username, child_firstname, parent_email ):
	"""
	Given a stream to our COPPA pdf, manipulate the fields to include the given data,
	and return a new read stream.

	This process is intimately tied to the structure of the PDF. If the PDF changes, then this
	process will have to be (slightly) recalculated. Thus this method is littered with assertions.

	This process depends on using standard PDF fonts, or having the
	entire font embedded, otherwise characters not contained in the
	PDF will fail to render (will render as square boxes). Our starter
	PDF includes all the ASCII characters, except the lowercase 'j',
	which causes text strings to break up. It has also been run
	through Acrobat Pro to be sure that the fields we want to replace
	are in Helvetica (Bold), and that this font (a standard font) is
	not subsetted, so that we can render 'j'. Acrobat Pro is also used to add the
	clickable link, which doesn't make it through printing from Word.

	The best way to get the document out of Word is to Print, use the
	PDF option of the Print dialog and 'Save as Adobe PDF', and
	'Smallest File Size' which puts it right into Acrobat. This is the
	only way to achieve the ~40K file size (otherwise you get 800K). When using the PDF Optimizer,
	image optimizations should be unchecked; having it checked seems to embed 300K of Color Space data.
	"""

	pdf_reader = pyPdf.PdfFileReader( pdf_stream )
	assert pdf_reader.numPages == 1

	pdf_page = pdf_reader.getPage( 0 )
	# Get the content (we have to decode it, if we ask the page to decode it, it
	# doesn't hold the reference)
	page_content = pyPdf.pdf.ContentStream( pdf_page['/Contents'].getObject(), pdf_page.pdf )
	# And store the content back in the page, under the NamedObject key, which happens to be equal to the string
	assert pdf_page.keys()[0] == '/Contents'
	pdf_page[pdf_page.keys()[0]] = page_content


	IX_UNAME = 366
	IX_FNAME = 385
	IX_EMAIL = 401

	assert page_content.operations[IX_EMAIL][1] == 'TJ' # TJ being the 'text with placement' operator
	assert page_content.operations[IX_UNAME][1] == 'TJ'
	assert page_content.operations[IX_FNAME][1] == 'TJ'

	def _pdf_clean( text ):
		# Many punctuation characters are handled specially and overlap
		# each other. They don't work in the Tj operator.
		# We can get pretty close with some padding.
		return text.replace( '-', '-  ' ).replace( '_', '_  ' ).replace( 'j', 'j ' )

	page_content.operations[IX_EMAIL] = ( [pyPdf.generic.TextStringObject( _pdf_clean(parent_email) )], 'Tj') # Tj being the simple text operator
	page_content.operations[IX_UNAME] = ( [pyPdf.generic.TextStringObject( _pdf_clean(username) )], 'Tj')
	page_content.operations[IX_FNAME] = ( [pyPdf.generic.TextStringObject( child_firstname )], 'Tj')


	writer = pyPdf.PdfFileWriter()
	writer.addPage( pdf_page )

	stream = StringIO()
	writer.write( stream )

	return StringIO( stream.getvalue() )
