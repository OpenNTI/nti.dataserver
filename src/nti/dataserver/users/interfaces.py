#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User related interfaces.

.. note:: Currently, the interfaces implemented in this package are spread across
	this module, and :mod:`nti.dataserver.interfaces`.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import re
import codecs
import string
import pkg_resources

from zope import component
from zope import interface

from zope.interface import Interface
from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from zope.schema import URI

from z3c.password.interfaces import NoPassword
from z3c.password.interfaces import InvalidPassword

from z3c.schema.email import isValidMailAddress

from plone.i18n.locales.interfaces import ICcTLDInformation

from nti.mailer.interfaces import IEmailAddressable

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import Date
from nti.schema.field import Object
from nti.schema.field import HTTPURL
from nti.schema.field import Variant
from nti.schema.field import TextLine
from nti.schema.field import ValidURI
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.interfaces import InvalidValue
from nti.schema.jsonschema import TAG_HIDDEN_IN_UI, TAG_UI_TYPE
from nti.schema.jsonschema import TAG_REQUIRED_IN_UI, TAG_READONLY_IN_UI

from nti.dataserver_fragments.schema import ExtendedCompoundModeledContentBody

from ..interfaces import InvalidData
from ..interfaces import checkCannotBeBlank
from ..interfaces import FieldCannotBeOnlyWhitespace

class UsernameCannotBeBlank(FieldCannotBeOnlyWhitespace):

	i18n_message = _("The username cannot be blank.")

	def __init__( self, username ):
		super(UsernameCannotBeBlank,self).__init__( 'Username', username )

class UsernameContainsIllegalChar(InvalidData):

	def __init__( self, username, allowed_chars ):
		self.username = username
		allowed_chars = set(allowed_chars) - set( string.letters + string.digits )
		allowed_chars = ''.join( sorted(allowed_chars) )
		self.allowed_chars = allowed_chars
		if not allowed_chars:
			allowed_chars = 'no special characters'
		self.i18n_message = _(
			'Username contains an illegal character. Only letters, digits, and ${allowed_chars} are allowed.',
			mapping={'allowed_chars': allowed_chars})

		super(UsernameContainsIllegalChar,self).__init__( self.i18n_message, 'Username',
														  username, value=username )

	def new_instance_restricting_chars( self, restricted_chars ):
		allowed_chars = set(self.allowed_chars) - set(restricted_chars)
		return type(self)( self.username, allowed_chars )

class EmailAddressInvalid(InvalidData):
	"""
	Invalid email address.
	"""

	i18n_message = _("The email address you have entered is not valid.")

	def __init__( self, address ):
		super(EmailAddressInvalid,self).__init__( address, value=address )

class RealnameInvalid(InvalidData):
	"""
	Invalid realname.
	"""

	field = 'realname'
	i18n_message = _("The first or last name you have entered is not valid.")

	def __init__( self, name ):
		super(RealnameInvalid,self).__init__( name, value=name )

class BlankHumanNameError(RealnameInvalid):

	def __init__(self, name=''):
		super(BlankHumanNameError,self).__init__(name)

class OldPasswordDoesNotMatchCurrentPassword(InvalidPassword):
	i18n_message = _("The password you supplied does not match the current password.")

class PasswordCannotConsistOfOnlyWhitespace(NoPassword):
	i18n_message = _("Your pasword cannot contain only whitespace. Please try again.")

class InsecurePasswordIsForbidden(InvalidPassword):
	i18n_message = _("The password you supplied has been identified by security researchers as commonly used and insecure. Please try again.")

	def __init__( self, value=None ):
		super(InsecurePasswordIsForbidden,self).__init__()
		if value:
			self.value = value

resource_stream = getattr(pkg_resources, 'resource_stream')

def _load_resource(n, f):
	stream = resource_stream( n, f )
	reader = codecs.getreader('utf-8')(stream)
	domains = set()
	for line in reader:
		line = line.strip()
		if not line or line.startswith('#'):
			continue
		line = line.upper()

		domains.add( line )
	return domains

# 2012-12-07: This list of passwords, identified by industry researchers,
# as extremely common and in all the rainbow tables, etc, is forbidden
# see http://arstechnica.com/gadgets/2012/12/blackberry-has-had-it-up-to-here-with-your-terrible-passwords/
_VERBOTEN_PASSWORDS = _load_resource( __name__, 'verboten-passwords.txt' )
del _load_resource

def _checkEmailAddress(address):
	""" Check email address.

	This should catch most invalid but no valid addresses.
	"""
	if not isValidMailAddress(address):
		raise EmailAddressInvalid(address)

	cctlds = component.getUtility(ICcTLDInformation)
	domain = address.rsplit( '.', 1 )[-1]
	if domain.lower() not in cctlds.getAvailableTLDs():
		raise EmailAddressInvalid(address)
	return True

def _isValidEmail(email):
	""" checks for valid email """
	_checkEmailAddress(email)
	return True

def checkEmailAddress(value):
	if value and _isValidEmail(value):
		return True
	raise EmailAddressInvalid( value )

#: A sequence of only non-alphanumeric characters
#: or a sequence of only digits and spaces, the underscore, and non-alphanumeric characters
#: (which is basically \W with digits and _ added back
_INVALID_REALNAME_RE = re.compile( r'^\W+$|^[\d\s\W_]+$', re.UNICODE )

def checkRealname(value):
	"""
	Ensure that the realname doesn't consist of just digits/spaces
	or just alphanumeric characters
	"""

	if value:
		if _INVALID_REALNAME_RE.match( value ):
			raise RealnameInvalid( value )
		# Component parts? TODO: What about 'Jon Smith 3' as 'Jon Smith III'?
		#for x in value.split():
	return True

class IWillUpdateNewEntityEvent(IObjectEvent):
	"""
	Fired before an :class:`zope.lifecycleevent.interfaces.IObjectCreatedEvent` with
	an entity that is in the process of being created by the factories. At this
	point, the entity will have only its username and parent established. Externalization
	details are yet to be filled in.

	This is a good opportunity to apply additional site-specific policies (interfaces),
	especially if they can guide the updating process.
	"""

	ext_value = interface.Attribute("The external value that will drive the update")
	meta_data = interface.Attribute("A dictionary with update meta data")

_marker = object()

@interface.implementer(IWillUpdateNewEntityEvent)
class WillUpdateNewEntityEvent(ObjectEvent):

	def __init__(self, obj, ext_value=_marker, meta_data=_marker):
		super(WillUpdateNewEntityEvent, self).__init__(obj)
		self.ext_value = ext_value if ext_value is not _marker else {}
		self.meta_data = meta_data if ext_value is not _marker else {}

class IWillCreateNewEntityEvent(IObjectEvent):
	"""
	Fired before an
	:class:`zope.lifecycleevent.interfaces.IObjectCreatedEvent` and
	after a :class:`IWillUpdateNewEntityEvent` with an entity that is
	in the process of being created by the factories. Externalization
	details will have been filled in.

	This is a good time to perform final validation of the entity.
	"""
	ext_value = interface.Attribute("If the entity was created with external data, this will be it.")
	meta_data = interface.Attribute("A dictionary with creation meta data")
	preflight_only = interface.Attribute("A boolean, set to true if this is a preflight-only event.")

@interface.implementer(IWillCreateNewEntityEvent)
class WillCreateNewEntityEvent(ObjectEvent):

	def __init__(self, obj, ext_value=None, preflight_only=False, meta_data=None):
		super(WillCreateNewEntityEvent, self).__init__(obj)
		self.ext_value = ext_value
		self.meta_data = meta_data
		self.preflight_only = preflight_only

class IWillUpdateEntityEvent(IObjectEvent):
	"""
	Fired before an updated is updated
	"""
	ext_value = interface.Attribute("External update data")

@interface.implementer(IWillUpdateEntityEvent)
class WillUpdateEntityEvent(ObjectEvent):

	def __init__(self, obj, ext_value=None):
		super(WillUpdateEntityEvent, self).__init__(obj)
		self.ext_value = ext_value

class IWillDeleteEntityEvent(IObjectEvent):
	"""
	Fired before an :class:`zope.lifecycleevent.interfaces.IObjectRemovedEvent` with
	an entity that is in the process of being deleted by the factories.
	"""

@interface.implementer(IWillDeleteEntityEvent)
class WillDeleteEntityEvent(ObjectEvent):

	def __init__( self, obj):
		super(WillDeleteEntityEvent,self).__init__( obj )

class IAvatarURLProvider(Interface):
	"""
	Something that can provide a display URL. This is separate
	from the profile hierarchy to allow delegation of adapters.
	"""

	avatarURL = URI(# may be data:
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

class IBackgroundURLProvider(Interface):
	"""
	Something that can provide a background URL. This is separate
	from the profile hierarchy to allow delegation of adapters.
	"""

	backgroundURL = URI(# may be data:
		title="URL of your background picture",
		description="If not provided, one will be generated for you.",
		required=False )

class IAvatarURL(Interface):
	"""
	Something that features a display URL.
	"""

	avatarURL = URI(# may be data:
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

IAvatarURL['avatarURL']._type = (str,unicode) # Relax this constraint for the sake of BWC

class IBackgroundURL(Interface):

	backgroundURL = URI(# may be data:
		title="URL of your background picture",
		description="If not provided, one will be generated for you.",
		required=False )

IBackgroundURL['backgroundURL']._type = (str,unicode) # Relax this constraint for the sake of BWC

class IProfileAvatarURL(IAvatarURL, IBackgroundURL):
	pass

class IAvatarChoices(Interface):
	"""
	Something that can provide choices for possible avatar URLs.
	Typically this will be registered as an adapter from a string (the username/email)
	or the IUser object. It may named for the site.
	"""
	# TODO: This is quite similar to a vocabulary
	def get_choices():
		"""
		Returns a sequence of string choices.
		"""

class IFriendlyNamed(Interface):

	alias = TextLine(
		title='Display alias',
		description="Enter preferred display name alias, e.g., johnnyboy."
			"Your site may impose limitations on this value.",
		required=False)

	realname = TextLine(
		title='Full Name aka realname',
		description="Enter full name, e.g. John Smith.",
		required=False,
		constraint=checkRealname)

	def get_searchable_realname_parts():
		"""
		Return an iterable of the parsed non-empty parts of the realname,
		excluding such things as title and suffix (things typically not
		helpful in search results).
		"""

class IImmutableFriendlyNamed(Interface):
	"""
	Apply this to a context object to mark that it should not allow mutation
	of the friendly name values.
	"""

	alias = TextLine(
		title='Display alias',
		description="Enter preferred display name alias, e.g., johnnyboy."
			"Your site may impose limitations on this value.",
		required=False,
		readonly=True)

	realname = TextLine(
		title='Full Name aka realname',
		description="Enter full name, e.g. John Smith.",
		required=False,
		readonly=True,
		constraint=checkRealname)

class IRequireProfileUpdate(Interface):
	"""
	Apply this as a marker to a context object (user) that requires a profile
	update. This will trigger profile validation (which usually doesn't happen)
	and allow bypassing certain parts of :class:`IImmutableFriendlyNamed.`
	"""

IFriendlyNamed['realname'].setTaggedValue( TAG_REQUIRED_IN_UI, True )

class IUserProfile(IFriendlyNamed, IProfileAvatarURL):
	"""
	Base class that user profiles should extend.
	"""

from nti.schema.jsonschema import UI_TYPE_EMAIL, UI_TYPE_HASHED_EMAIL

class IRestrictedUserProfile(IUserProfile):
	"""
	A profile for a restricted user.
	"""

	birthdate = Date(
		title='birthdate',
		description='Your date of birth. '
			'If one is not provided, you will be assumed to be underage.',
		required=False )

	password_recovery_email_hash = ValidTextLine(
		title="A secure hash of an email address used during password recovery",
		description="Typically auto-generated by setting the `email` field.",
		required=False )
	password_recovery_email_hash.setTaggedValue( TAG_HIDDEN_IN_UI, True )
	password_recovery_email_hash.setTaggedValue( TAG_READONLY_IN_UI, True )
	password_recovery_email_hash.setTaggedValue( TAG_UI_TYPE, UI_TYPE_HASHED_EMAIL )

	email = ValidTextLine(
		title='Email',
		description=u'Email is not stored at this level, but the field is specified here as a convenient way'
			' to be able to set the password_recovery_email_hash',
		required=False,
		constraint=checkEmailAddress)
	email.setTaggedValue( TAG_UI_TYPE, UI_TYPE_HASHED_EMAIL )

	email_verified = Bool(
		title="Has the email been verified?",
		required=False,
		default=False )
	email_verified.setTaggedValue( TAG_HIDDEN_IN_UI, True )
	email_verified.setTaggedValue( TAG_READONLY_IN_UI, True )

class IRestrictedUserProfileWithContactEmail(IRestrictedUserProfile):
	"""
	A profile that adds a (temporary) contact email during the account setup
	process.
	"""

	contact_email = ValidTextLine(
		title='Contact email',
		description=u"An email address to use to contact someone responsible for this accounts' user",
		required=False,
		constraint=checkEmailAddress)

	contact_email.setTaggedValue( TAG_REQUIRED_IN_UI, True )
	contact_email.setTaggedValue( TAG_UI_TYPE, UI_TYPE_EMAIL )

class IContactEmailRecovery(interface.Interface):
	"""
	Information used for recovering/resending consent emails to
	COPPA users, since we cannot actually retain the contact email.
	Should be registered as an adapter on the user.
	"""
	contact_email_recovery_hash = interface.Attribute( "A string giving the hash of the contact email.")
	consent_email_last_sent = interface.Attribute( "A float giving the time the last consent email was sent.")

class ISocialMediaProfile(interface.Interface):
	"""
	A social media profile
	"""

	facebook = ValidURI(title='facebook',
						description=u'The Facebook URL',
						required=False)

	twitter = ValidURI(title='twitter',
					   description=u'The twitter URL',
					   required=False)

	googlePlus = ValidURI(title='GooglePlus',
					  	  description=u'The GooglePlus URL',
					   	  required=False)

	linkedIn = ValidURI(title='linkedIn',
					  	description=u'The LinkedIn URL',
					   	required=False)


class IEducation(interface.Interface):

	school = ValidTextLine(title='School name',
						   description=u'School name.',
						   required=True)

	startYear = Int(title='Start year',
					description=u'Start year',
					required=False)

	endYear = Int(title='End year',
				  description=u'End year',
				  required=False)

	degree = ValidTextLine(title='Degree name',
				 		   description=u'Degree name',
				  		   required=False)

	description = ValidText(title='Degree description',
				 		   	description=u'Degree description',
				  		   	required=False)

class IEducationProfile(interface.Interface):
	"""
	A social media profile
	"""

	education = ListOrTuple(Object(IEducation, title="The education entry"),
							title="Education entries",
							required=False,
							min_length=0)

class IProfessionalPosition(interface.Interface):

	companyName = ValidTextLine(title='Company name',
						   		description=u'CompanyName name.',
						   		required=True)

	title = ValidTextLine(title='Title',
						  description=u'Title',
						  required=True)

	startYear = Int(title='Start year',
					description=u'Start year',
					required=True)

	endYear = Int(title='End year',
				  description=u'End year',
				  required=False)

	description = ValidText(title='Position description',
				 		   	description=u'Position description',
				  		   	required=False)
IPosition = IProfessionalPosition

class IProfessionalProfile(interface.Interface):
	"""
	A professional profile
	"""

	positions = ListOrTuple(Object(IProfessionalPosition, title="The profesional position entry"),
							title="profesional position entries",
							required=False,
							min_length=0)

class IInterestProfile(interface.Interface):
	"""
	A Interest profile
	"""

	interests = ListOrTuple(ValidTextLine(title="An interest"),
							title="interest entries",
							required=False,
							min_length=0)

class IAboutProfile(interface.Interface):

	about = Variant((ValidText(title='About',
							  description="A description of a user",
							  required=False,
							  constraint=checkCannotBeBlank),
					 ExtendedCompoundModeledContentBody()),
					 description="The body is either a string, or a Note body")
	about.__name__ = 'about'

class ICompleteUserProfile(IRestrictedUserProfile,
						   IEmailAddressable,
						   ISocialMediaProfile,
						   IEducationProfile,
						   IProfessionalProfile,
						   IInterestProfile,
						   IAboutProfile):
	"""
	A complete user profile.
	"""

	email = ValidTextLine(
		title='Email',
		description=u'An email address that can be used for communication.',
		required=False,
		constraint=checkEmailAddress)
	email.setTaggedValue( TAG_UI_TYPE, UI_TYPE_EMAIL )

	opt_in_email_communication = Bool(
		title="Can we contact you by email?",
		required=False,
		default=False )

	home_page = HTTPURL(
		title='Home page',
		description="The URL for your external home page, "
					  "if you have one.",
		required=False)

	description = ValidText(
		title='Biography',
		description="A short overview of who you are and what you "
					  "do. Will be displayed on your author page, linked "
					  "from the items you create.",
		max_length=140, # twitter
		required=False,
		constraint=checkCannotBeBlank)

	location = ValidTextLine(
		title='Location',
		description="Your location - either city and "
					  "country - or in a company setting, where "
					  "your office is located.",
		required=False,
		constraint=checkCannotBeBlank)

	# TODO: This probably comes from a vocabulary, at least for some users
	affiliation = ValidTextLine(
		title='Affiliation',
		description="Your affiliation, such as school name",
		max_length=140,
		required=False,
		constraint=checkCannotBeBlank)

	role = ValidTextLine(
		title='Role',
		description="Your role within your affiliation",
		max_length=140,
		required=False,
		constraint=checkCannotBeBlank)

class IEmailRequiredUserProfile(ICompleteUserProfile):
	"""
	A user profile that ensures the email is filled in.

	.. note:: This is temporary and will become an alias for :class:`ICompleteUserProfile`
		when tests are updated across the board to require email addresses.
	"""

	email = ValidTextLine(
		title='Email',
		description=u'',
		required=True, # TODO: This should move up when ready
		constraint=checkEmailAddress)
	email.setTaggedValue( TAG_UI_TYPE, UI_TYPE_EMAIL )

class IUserProfileSchemaProvider(Interface):
	"""
	Usually registered as an adapter from a IUser interface or sometimes an IEntity.

	This is used during the externalization process to determine
	what sort of data we should require or provide.
	"""

	def getSchema():
		"""
		Return the interface that defines the profile data expected.
		"""

@interface.implementer(IUserProfileSchemaProvider)
class FriendlyNamedSchemaProvider(object):
	"""
	Return the base IFriendlyNamed profile. This will work as an
	adapter for anything that extends Entity, and the most derived available
	profile will be used (that is registered as an adapter for that type).
	"""
	def __init__( self, context ):
		pass

	def getSchema(self):
		return IFriendlyNamed

class ICommunityProfile(IAvatarURL, IAboutProfile):

	backgroundURL = URI(# may be data:
		title="URL of your background picture",
		required=False )

ICommunityProfile['avatarURL']._type = (str,unicode) # relax
ICommunityProfile['backgroundURL']._type = (str,unicode) # relax

class BlacklistedUsernameError(InvalidValue):
	"""
	Indicates the given username has been blacklisted.
	"""
	pass

class EmailAlreadyVerifiedError(InvalidValue):
	"""
	Indicates the given email has been verified by another user.
	"""
	pass

class IRecreatableUser(Interface):
	"""
	Apply this as a marker to a context object (user) that can be
	recreated (e.g. not blacklisted).  This is useful for unit tests
	that create and destroy users.
	"""

class ISendEmailConfirmationEvent(IObjectEvent):
	"""
	A event to send a email confirmation email
	"""

	user = interface.Attribute("User to send the confirmation email to.")
	request = interface.Attribute("A request object")

@interface.implementer(ISendEmailConfirmationEvent)
class SendEmailConfirmationEvent(ObjectEvent):

	def __init__(self, obj, request=None):
		super(SendEmailConfirmationEvent, self).__init__(obj)
		self.request = request

	@property
	def user(self):
		return self.object

def validateAccept(value):
	if not value == True:
		return False
	return True

# Membership.

class IDisallowActivityLink(interface.Interface):
	"""
	marker interface to disallow activity link
	"""

class IDisallowMembersLink(interface.Interface):
	"""
	marker interface to disallow members link
	"""

class IDisallowHiddenMembership(interface.Interface):
	"""
	marker interface to disallow hidden memberships
	"""

class IDisallowMembershipOperations(IDisallowMembersLink,
									IDisallowActivityLink,
									IDisallowHiddenMembership):
	pass

class IHiddenMembership(interface.Interface):

	def hide(entity):
		"""
		hide the memebership for the specified entity
		"""

	def unhide(self, entity):
		"""
		unhide the memebership for the specified entity
		"""

	def __contains__(entity):
		"""
		check if membership of the specifed entity is hidden
		"""

# Suggested contacts.

class ISuggestedContactRankingPolicy(Interface):
	"""
	Defines a user ranking policy for a provider. This policy
	defines the order in which the suggestions are returned
	"""

	priority = Int(title="Provider prority", required=False, default=1)

	def sort(contacts):
		"""
		sort the specified suggested contacts
		"""

class ISuggestedContactsProvider(Interface):

	"""
	Defines a utility that allows to return contact suggestions for a user
	"""

	ranking = Object(ISuggestedContactRankingPolicy, title="Ranking policy",
					 required=False)

	context = Object(Interface, title="Provider context",
					 required=False)

	def suggestions(user):
		"""
		return a iterator with suggested contacts ordered by the ranking policy
		"""

class ISuggestedContact(Interface):
	username = ValidTextLine(title="username", required=True)
	rank = Int(title="contact rank", required=False, default=1)

def get_all_suggested_contacts(user):
	"""
	Scan all registered ISuggestedContactsProvider and return their suggestions
	"""
	for _, provider in list(component.getUtilitiesFor(ISuggestedContactsProvider)):
		for suggestion in provider.suggestions(user):
			suggestion.provider = provider
			yield suggestion
