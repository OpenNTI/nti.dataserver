#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User related interfaces.

.. note:: Currently, the interfaces implemented in this package are spread across
	this module, and :mod:`nti.dataserver.interfaces`.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import re
import string
import codecs
import pkg_resources

from zope import schema
from zope import interface
from zope import component
from zope.i18n import translate
from zope.interface import Interface
from zope.interface.common.mapping import IMapping

import zope.component.interfaces

from z3c.password import interfaces as pwd_interfaces
from plone.i18n.locales import interfaces as locale_interfaces

import nti.utils.schema
from nti.utils.schema import ValidText
from nti.utils.schema import ValidTextLine
from nti.utils.jsonschema import TAG_HIDDEN_IN_UI, TAG_UI_TYPE, TAG_REQUIRED_IN_UI, TAG_READONLY_IN_UI

class _InvalidData(nti.utils.schema.InvalidValue):
	"""Invalid Value"""

	i18n_message = None

	def __str__(self):
		if self.i18n_message:
			return translate(self.i18n_message)
		return super(_InvalidData, self).__str__()

	def doc(self):
		if self.i18n_message:
			return self.i18n_message
		return self.__class__.__doc__

class FieldCannotBeOnlyWhitespace(_InvalidData):

	i18n_message = _("The field cannot be blank.") # TODO: Not very good

	def __init__( self, field_name, value, field_external=None ):
		super(FieldCannotBeOnlyWhitespace,self).__init__( self.i18n_message,
														  field_external or (field_name and field_name.capitalize()),
														  value,
														  value=value )

def checkCannotBeBlank(value):
	if not value or not value.strip():
		raise FieldCannotBeOnlyWhitespace( None, value )

	return True

class UsernameCannotBeBlank(FieldCannotBeOnlyWhitespace):

	i18n_message = _("The username cannot be blank.")

	def __init__( self, username ):
		super(UsernameCannotBeBlank,self).__init__( 'Username', username )

class UsernameContainsIllegalChar(_InvalidData):

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

		super(UsernameContainsIllegalChar,self).__init__( self.i18n_message, 'Username', username, value=username )

	def new_instance_restricting_chars( self, restricted_chars ):
		allowed_chars = set(self.allowed_chars) - set(restricted_chars)
		return type(self)( self.username, allowed_chars )

class EmailAddressInvalid(_InvalidData):
	"""Invalid email address."""

	i18n_message = _("The email address you have entered is not valid.")

	def __init__( self, address ):
		super(EmailAddressInvalid,self).__init__( address, value=address )

class RealnameInvalid(_InvalidData):
	""" Invalid realname. """
	i18n_message = _("The first or last name you have entered is not valid.")
	field = 'realname'

	def __init__( self, name ):
		super(RealnameInvalid,self).__init__( name, value=name )


class OldPasswordDoesNotMatchCurrentPassword(pwd_interfaces.InvalidPassword):
	i18n_message = _("The password you supplied does not match the current password.")

class PasswordCannotConsistOfOnlyWhitespace(pwd_interfaces.NoPassword):
	i18n_message = _("Your pasword cannot contain only whitespace. Please try again.")

class InsecurePasswordIsForbidden(pwd_interfaces.InvalidPassword):
	i18n_message = _("The password you supplied has been identified by security researches as commonly used and insecure. Please try again.")

	def __init__( self, value=None ):
		super(InsecurePasswordIsForbidden,self).__init__()
		if value:
			self.value = value


# Email validation functions. With the exception of _load_valid_domain_list and its use,
# these are based on some Zope/Plone code

# RFC 2822 local-part: dot-atom or quoted-string
# characters allowed in atom: A-Za-z0-9!#$%&'*+-/=?^_`{|}~
# RFC 2821 domain: max 255 characters
_LOCAL_RE = re.compile(r'([A-Za-z0-9!#$%&\'*+\-/=?^_`{|}~]+'
                     r'(\.[A-Za-z0-9!#$%&\'*+\-/=?^_`{|}~]+)*|'
                     r'"[^(\|")]*")@[^@]{3,255}$')

# RFC 2821 local-part: max 64 characters
# RFC 2821 domain: sequence of dot-separated labels
# characters allowed in label: A-Za-z0-9-, first is a letter
# Even though the RFC does not allow it all-numeric labels do exist
_DOMAIN_RE = re.compile(r'[^@]{1,64}@[A-Za-z0-9][A-Za-z0-9-]*'
                                r'(\.[A-Za-z0-9][A-Za-z0-9-]*)+$')

EMAIL_RE = re.compile(r"^(\w&.%#$&'\*+-/=?^_`{}|~]+!)*[\w&.%#$&'\*+-/=?^_`{}|~]+@(([0-9a-z]([0-9a-z-]*[0-9a-z])?\.)+[a-z]{2,6}|([0-9]{1,3}\.){3}[0-9]{1,3})$", re.IGNORECASE)

def _load_resource(n, f):
	stream = pkg_resources.resource_stream( n, f )
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
	if not _LOCAL_RE.match(address):
		raise EmailAddressInvalid(address)
	if not _DOMAIN_RE.match(address):
		raise EmailAddressInvalid(address)

	cctlds = component.getUtility(locale_interfaces.ICcTLDInformation)
	domain = address.rsplit( '.', 1 )[-1]
	if domain.lower() not in cctlds.getAvailableTLDs():
		raise EmailAddressInvalid(address)
	return True

def _isValidEmail(email):
	""" checks for valid email """
	if EMAIL_RE.search(email) == None:
		raise EmailAddressInvalid(email)

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

class IWillUpdateNewEntityEvent(zope.component.interfaces.IObjectEvent):
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
class WillUpdateNewEntityEvent(zope.component.interfaces.ObjectEvent):

	def __init__(self, obj, ext_value=_marker, meta_data=_marker):
		super(WillUpdateNewEntityEvent, self).__init__(obj)
		self.ext_value = ext_value if ext_value is not _marker else {}
		self.meta_data = meta_data if ext_value is not _marker else {}

class IWillCreateNewEntityEvent(zope.component.interfaces.IObjectEvent):
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
class WillCreateNewEntityEvent(zope.component.interfaces.ObjectEvent):

	def __init__(self, obj, ext_value=None, preflight_only=False, meta_data=None):
		super(WillCreateNewEntityEvent, self).__init__(obj)
		self.ext_value = ext_value
		self.meta_data = meta_data
		self.preflight_only = preflight_only

class IWillDeleteEntityEvent(zope.component.interfaces.IObjectEvent):
	"""
	Fired before an :class:`zope.lifecycleevent.interfaces.IObjectRemovedEvent` with
	an entity that is in the process of being deleted by the factories.
	"""

@interface.implementer(IWillUpdateNewEntityEvent)
class WillDeleteEntityEvent(zope.component.interfaces.ObjectEvent):

	def __init__( self, obj):
		super(WillDeleteEntityEvent,self).__init__( obj )

class IAvatarURLProvider(Interface):
	"""
	Something that can provide a display URL. This is separate
	from the profile hierarchy to allow delegation of adapters.
	"""

	avatarURL = schema.URI( # may be data:
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

class IAvatarURL(Interface):
	"""
	Something that features a display URL.
	"""

	avatarURL = schema.URI( # may be data:
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

IAvatarURL['avatarURL']._type = (str,unicode) # Relax this constraint for the sake of BWC

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

	alias = schema.TextLine(
		title='Display alias',
		description="Enter preferred display name alias, e.g., johnnyboy."
			"Your site may impose limitations on this value.",
		required=False)

	realname = schema.TextLine(
		title='Full Name aka realname',
		description="Enter full name, e.g. John Smith.",
		required=False,
		constraint=checkRealname)

class IImmutableFriendlyNamed(Interface):
	"""
	Apply this to a context object to mark that it should not allow mutation
	of the friendly name values.
	"""

	alias = schema.TextLine(
		title='Display alias',
		description="Enter preferred display name alias, e.g., johnnyboy."
			"Your site may impose limitations on this value.",
		required=False,
		readonly=True)

	realname = schema.TextLine(
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

class IUserProfile(IFriendlyNamed, IAvatarURL):
	"""
	Base class that user profiles should extend.
	"""

UI_TYPE_EMAIL = 'nti.dataserver.users.interfaces.EmailAddress'
UI_TYPE_HASHED_EMAIL = UI_TYPE_EMAIL + ":Hashed" # So that a begins-with test will match either, making validation easier

class IRestrictedUserProfile(IUserProfile):
	"""
	A profile for a restricted user.
	"""

	birthdate = schema.Date(
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


class ICompleteUserProfile(IRestrictedUserProfile):
	"""
	A complete user profile.
	"""

	email = ValidTextLine(
		title='Email',
		description=u'An email address that can be used for communication.',
		required=False,
		constraint=checkEmailAddress)
	email.setTaggedValue( TAG_UI_TYPE, UI_TYPE_EMAIL )

	opt_in_email_communication = schema.Bool(
		title="Can we contact you by email?",
		required=False,
		default=False )

	home_page = nti.utils.schema.HTTPURL(
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

	about = ValidTextLine(
		title='About',
		description="A short description of a user",
		max_length=500,
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

def validateAccept(value):
	if not value == True:
		return False
	return True

from zope.deprecation import deprecated
class IEntityPreferences(IMapping):
	"""
	Something that can store key value data for an entity
	"""

deprecated('IEntityPreferences', 'Use zope.prefereces')
