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

import time

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

from nti.utils.property import annotation_alias
from nti.utils.schema import IBeforeTextAssignedEvent

from nti.appserver import site_policies

@component.adapter(nti_interfaces.IModeledContent, IObjectCreatedEvent)
def dispatch_content_created_to_user_policies( content, event ):
	component.handle( content, content.creator, event )

from pyramid import security as psec
from pyramid.threadlocal import get_current_request
from nti.dataserver import users
from nti.dataserver.users import user_profile

@component.adapter(nti_interfaces.IModeledContent, IObjectModifiedEvent)
def dispatch_content_edited_to_user_policies( content, event ):
	request = get_current_request()
	if request is None:
		return
	# TODO: This interacts funny with chat events. There is no current request, but
	# there may be an authentication policy installed, which can lead to repoze.who
	# throwing errors. In some places in chat we install our own authentication policy,
	# but not everywhere. See the following stack trace.
	editor = users.User.get_user( psec.authenticated_userid( request ) )
	component.handle( content, editor, event )

# Traceback (most recent call last):
#   File "nti/socketio/session_consumer.py", line 150, in _on_msg
#     result = handler( )
#   File "nti/socketio/session_consumer.py", line 119, in call
#     result = h(*args)
#   File "nti/chatserver/_handler.py", line 198, in enterRoom
#     room = self._chatserver.create_room_from_dict( room_info, sessions_validator=sessions_validator )
#   File "nti/chatserver/chatserver.py", line 359, in create_room_from_dict
#     internalization.update_from_external_object( room, room_info_dict, context=ds )
#   File "nti/externalization/internalization.py", line 292, in update_from_external_object
#     lifecycleevent.modified( containedObject, *attributes )
#   File "/zope/lifecycleevent/__init__.py", line 109, in modified
#     notify(ObjectModifiedEvent(object, *descriptions))
# ...
#   File "nti/appserver/user_policies.py", line 55, in dispatch_content_edited_to_user_policies
#     editor = users.User.get_user( psec.authenticated_userid( get_current_request() ) )
#   File "/pyramid-1.4b1-py2.7.egg/pyramid/security.py", line 71, in authenticated_userid
#     return policy.authenticated_userid(request)
#   File "/pyramid_who-0.3-py2.7.egg/pyramid_who/whov2.py", line 51, in authenticated_userid
#     identity = self._get_identity(request)
#   File "/pyramid_who-0.3-py2.7.egg/pyramid_who/whov2.py", line 87, in _get_identity
#     identity = request.environ.get('repoze.who.identity')
# AttributeError: 'NoneType' object has no attribute 'environ'

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

@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.IUser)
class MathCountsCapabilityFilter(site_policies.NoAvatarUploadCapabilityFilter):

	def __init__( self, context=None ):
		super(MathCountsCapabilityFilter, self).__init__(context)
		self.context = context

	def filterCapabilities( self, capabilities ):
		result = super(MathCountsCapabilityFilter, self).filterCapabilities(capabilities)

		# JAM: The 'role' value is not something suitable to base permissions on (it is never verified)
		# this filter should NOT be used unless it is extremely necessary
		profile = user_interfaces.IUserProfile(self.context) if self.context else None
		role = getattr(profile, 'role', None)
		if role is None or role.lower() in ('student', 'other'):
			result.discard(u'nti.platform.p2p.dynamicfriendslists')

		result.discard('nti.platform.blogging.createblogentry')
		result.discard('nti.platform.forums.communityforums' )
		return result

#: This relationship is exposed on Users and in the handshake/ping
#: when the UI should display it as a link to information about
#: our "Children's Privacy Policy." It is a permanent link.
#: NOTE: you may also get the :data:`REL_GENERAL_PRIVACY_PAGE` link
#: depending on the site and type of user.
REL_CHILDRENS_PRIVACY_PAGE = 'childrens-privacy'

#: Link relationship indicating the general privacy policy page
#: The client is expected to make this relationship
#: available to the end user at all times for review. It is NOT a deletable
#: link.
REL_GENERAL_PRIVACY_PAGE = 'content.permanent_general_privacy_page'


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

from pyramid.renderers import render
from pyramid.renderers import get_renderer
from pyramid_mailer.message import Message
from pyramid_mailer.message import Attachment
from email.mime.multipart import MIMEMultipart


CONTACT_EMAIL_RECOVERY_ANNOTATION = __name__ + '.contact_email_recovery_hash'
#: The time.time() value at which the last consent request
#: email was sent. Used to implement rate limiting. We apply rate limiting
#: even when changing as a result of a bounce
CONSENT_EMAIL_LAST_SENT_ANNOTATION = __name__ + '.consent_email_last_sent'

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


@component.adapter(dolmen.builtins.IUnicode, user_interfaces.IRestrictedUserProfileWithContactEmail, IBeforeTextAssignedEvent)
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
	_send_consent_request( user, profile, new_email, event, rate_limit=True )
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

class AttemptingToResendConsentEmailTooSoon(sch_interfaces.ValidationError):
	i18n_message = _("It is too soon to send another consent request email. Please try again tomorrow.")
	field = 'contact_email'

def _send_consent_request( user, profile, email, event, rate_limit=False ):

	if not email:
		return

	if not event.request: #pragma: no cover
		return

	recovery_info = app_interfaces.IContactEmailRecovery( user )
	if rate_limit:
		time_last_sent = recovery_info.consent_email_last_sent or 0
		a_day_after_last_sent = time_last_sent + (12 * 60 * 60) # twelve hour lockout
		if time.time() < a_day_after_last_sent:
			raise AttemptingToResendConsentEmailTooSoon()

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

	# Prefill the fields.
	attachment_stream = _alter_pdf( attachment_filename, user.username, profile.realname, email )
	attachment = Attachment(attachment_filename, "application/pdf", attachment_stream )

	message = Message( subject=_("Please Confirm Your Child's NextThought Account"),
					   recipients=[email],
					   sender='NextThought No Reply <no-reply@nextthought.com>', # match default, required for to_message()
					   body=text_body,
					   html=html_body,
					   attachments=[attachment] )
	# It's a bit tricky to do alternative body parts plus attachments. It requires
	# a nested MIME structure, which, prior to 0.11, Message won't do by default:
	# multipart/mixed
	#  |\
	#  | - multipart/alternative
	#  |  \
	#  |   - text/plain
	#  |   - text/html
	#  |\
	#    - application/pdf; content-disposition: attachment
	#
	# (See http://stackoverflow.com/questions/3902455/smtp-multipart-alternative-vs-multipart-mixed)
	# In the past, we had to do this manually, as of 0.11 it is handled for us.

	_email_utils.send_pyramid_mailer_mail( message )

	# We can log that we sent the message to the contact person for operational purposes,
	# but legally we cannot preserve it in the database
	logger.info( "Will send COPPA consent notice to %s on behalf of %s", email, user.username )
	setattr( profile, 'contact_email', None )

	# We do need to keep something machine readable, though, for purposes of bounces
	recovery_info.contact_email_recovery_hash = user_profile.make_password_recovery_email_hash( email )
	recovery_info.consent_email_last_sent = time.time()

def _clear_consent_email_rate_limit( user ):
	annotations = IAnnotations(user)
	if CONSENT_EMAIL_LAST_SENT_ANNOTATION in annotations:
		del annotations[CONSENT_EMAIL_LAST_SENT_ANNOTATION]

@interface.implementer(app_interfaces.IContactEmailRecovery)
@component.adapter(nti_interfaces.IUser)
class ContactEmailRecovery(object):
	"""
	For backward compatibility, stores values in annotations directly
	on the user
	"""

	def __init__( self, context ):
		self.context = context

	contact_email_recovery_hash = annotation_alias(CONTACT_EMAIL_RECOVERY_ANNOTATION, 'context')
	consent_email_last_sent = annotation_alias(CONSENT_EMAIL_LAST_SENT_ANNOTATION, 'context')

import pyPdf
import pyPdf.generic
from cStringIO import StringIO
try:
	from gevent.lock import RLock
except ImportError:
	from threading import RLock

# Reading the pristine PDF is fairly time consuming; fortunately, it
# returns a dict we can clone
_cached_pages = {} # filename => {page, contents, lock}
import zope.testing.cleanup
zope.testing.cleanup.addCleanUp( _cached_pages.clear )

def _alter_pdf( pdf_filename, username, child_firstname, parent_email ):
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
	only way to achieve the ~40K file size (otherwise you get 800K).
	When using the PDF Optimizer, image optimizations should be
	unchecked; having it checked seems to embed 300K of Color Space
	data. Also, the best results seem to come from simply unembedding all the
	fonts and setting compatibility to PDF 1.3.
	"""

	# The locations in the Contents array at which various things are
	# found
	IX_UNAME = 376
	IX_FNAME = 395
	IX_EMAIL = 411

	pdf_page, page_content, lock = _cached_pages.get( pdf_filename, (None, None, None) )
	if pdf_page is None:
		pdf_stream = pkg_resources.resource_stream( 'nti.appserver.templates',
													pdf_filename )
		pdf_reader = pyPdf.PdfFileReader( pdf_stream )
		assert pdf_reader.numPages == 1

		pdf_page = pdf_reader.getPage( 0 )
		lock = RLock()

		# Get the content (we have to decode it, if we ask the page to decode it, it
		# doesn't hold the reference)
		page_content = pyPdf.pdf.ContentStream( pdf_page['/Contents'].getObject(), pdf_page.pdf )
		# And store the content back in the page, under the NamedObject key
		# (which happens to be equal to the string, but IS NOT a string)
		page_key = None
		for key in pdf_page.keys():
			if key == '/Contents':
				page_key = key
				break
		assert page_key is not None
		pdf_page[page_key] = page_content

		# make sure we have the correct page
		assert page_content.operations[IX_EMAIL][1] == 'TJ' # TJ being the 'text with placement' operator
		assert page_content.operations[IX_UNAME][1] == 'TJ'
		assert page_content.operations[IX_FNAME][1] == 'TJ'

		_cached_pages[pdf_filename] = pdf_page, page_content, lock


	def _pdf_clean( text ):
		# Many punctuation characters are handled specially and overlap
		# each other. They don't work in the Tj operator.
		# We can get pretty close with some padding.
		return text.replace( '-', '-  ' ).replace( '_', '_  ' ).replace( 'j', 'j ' )

	writer = pyPdf.PdfFileWriter()
	stream = StringIO()
	with lock:
		page_content.operations[IX_EMAIL] = ( [pyPdf.generic.TextStringObject( _pdf_clean(parent_email) )], 'Tj') # Tj being the simple text operator
		page_content.operations[IX_UNAME] = ( [pyPdf.generic.TextStringObject( _pdf_clean(username) )], 'Tj')
		page_content.operations[IX_FNAME] = ( [pyPdf.generic.TextStringObject( child_firstname )], 'Tj')


		writer.addPage( pdf_page )
		writer.write( stream )

	stream.seek( 0 )
	return stream
