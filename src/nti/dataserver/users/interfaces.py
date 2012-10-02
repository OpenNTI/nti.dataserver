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

from zope import interface
from zope.interface import Interface
from zope import schema
import zope.schema.interfaces
import zope.component.interfaces

from z3c.password import interfaces as pwd_interfaces

import re
import string

from zope.i18n import translate
from . import MessageFactory as _

import nti.utils.schema

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

class UsernameCannotBeBlank(_InvalidData):

	i18n_message = _("The username cannot be blank.")

	def __init__( self, username ):
		super(UsernameCannotBeBlank,self).__init__( self.i18n_message, 'Username', username, value=username )

class UsernameContainsIllegalChar(_InvalidData):

	def __init__( self, username, allowed_chars ):
		self.username = username
		allowed_chars = set(allowed_chars) - set( string.letters + string.digits )
		allowed_chars = ''.join( allowed_chars )
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

class OldPasswordDoesNotMatchCurrentPassword(pwd_interfaces.InvalidPassword):
	i18n_message = _("The password you supplied does not match the current password.")

class PasswordCannotConsistOfOnlyWhitespace(pwd_interfaces.NoPassword):
	i18n_message = _("Your pasword cannot contain only whitespace. Please try again.")

# RFC 2822 local-part: dot-atom or quoted-string
# characters allowed in atom: A-Za-z0-9!#$%&'*+-/=?^_`{|}~
# RFC 2821 domain: max 255 characters
_LOCAL_RE = re.compile(r'([A-Za-z0-9!#$%&\'*+\-/=?^_`{|}~]+'
                     r'(\.[A-Za-z0-9!#$%&\'*+\-/=?^_`{|}~]+)*|'
                     r'"[^(\|")]*")@[^@]{3,255}$')

# RFC 2821 local-part: max 64 characters
# RFC 2821 domain: sequence of dot-separated labels
# characters allowed in label: A-Za-z0-9-, first is a letter
# Even though the RFC does not allow it all-numeric domains do exist
_DOMAIN_RE = re.compile(r'[^@]{1,64}@[A-Za-z0-9][A-Za-z0-9-]*'
                                r'(\.[A-Za-z0-9][A-Za-z0-9-]*)+$')

EMAIL_RE = re.compile(r"^(\w&.%#$&'\*+-/=?^_`{}|~]+!)*[\w&.%#$&'\*+-/=?^_`{}|~]+@(([0-9a-z]([0-9a-z-]*[0-9a-z])?\.)+[a-z]{2,6}|([0-9]{1,3}\.){3}[0-9]{1,3})$", re.IGNORECASE)


def _checkEmailAddress(address):
	""" Check email address.

	This should catch most invalid but no valid addresses.
	"""
	if not _LOCAL_RE.match(address):
		raise EmailAddressInvalid(address)
	if not _DOMAIN_RE.match(address):
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

class IWillUpdateNewEntityEvent(zope.component.interfaces.IObjectEvent):
	"""
	Fired before an :class:`zope.lifecycleevent.interfaces.IObjectCreatedEvent` with
	an entity that is in the process of being created by the factories. At this
	point, the entity will have only its username and parent established. Externalization
	details are yet to be filled in.

	This is a good opportunity to apply additional site-specific policies (interfaces),
	especially if they can guide the updating process.
	"""

	ext_value = interface.Attribute( "The external value that will drive the update" )

@interface.implementer(IWillUpdateNewEntityEvent)
class WillUpdateNewEntityEvent(zope.component.interfaces.ObjectEvent):

	def __init__( self, obj, ext_value=None ):
		super(WillUpdateNewEntityEvent,self).__init__( obj )
		self.ext_value = ext_value

class IWillCreateNewEntityEvent(zope.component.interfaces.IObjectEvent):
	"""
	Fired before an
	:class:`zope.lifecycleevent.interfaces.IObjectCreatedEvent` and
	after a :class:`IWillUpdateNewEntityEvent` with an entity that is
	in the process of being created by the factories. Externalization
	details will have been filled in.

	This is a good time to perform final validation of the entity.
	"""

@interface.implementer(IWillCreateNewEntityEvent)
class WillCreateNewEntityEvent(zope.component.interfaces.ObjectEvent):
	pass

class IAvatarURLProvider(Interface):
	"""
	Something that can provide a display URL. This is separate
	from the profile hierarchy to allow delegation of adapters.
	"""

	avatarURL = schema.URI(
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

class IAvatarURL(Interface):
	"""
	Something that features a display URL.
	"""

	avatarURL = schema.URI(
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
		required=False)

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
		readonly=True)

from nti.utils.schema import ValidTextLine as _ValidTextLine

TAG_HIDDEN_IN_UI = "nti.dataserver.users.field_hidden_in_ui" # Don't display this by default in the UI
TAG_UI_TYPE = 'nti.dataserver.users.field_type' # Qualifying details about how the field should be treated, such as data source
TAG_REQUIRED_IN_UI = 'nti.dataserver.users.field_required' # Overrides the value from the field itself
TAG_READONLY_IN_UI = 'nti.dataserver.users.field_readonly' # Overrides the value from the field itself, if true

class IUserProfile(IFriendlyNamed, IAvatarURL):
	"""
	Base class that user profiles should extend.
	"""

class IRestrictedUserProfile(IUserProfile):
	"""
	A profile for a restricted user.
	"""

	birthdate = schema.Date(
		title='birthdate',
		description='Your date of birth. '
			'If one is not provided, you will be assumed to be underage.',
		required=False )

	password_recovery_email_hash = _ValidTextLine(
		title="A secure hash of an email address used during password recovery",
		description="Typically auto-generated by setting the `email` field.",
		required=False )

	email = _ValidTextLine(
		title='Email',
		description=u'Email is not stored at this level, but the field is specified here as a convenient way'
			' to be able to set the password_recovery_email_hash',
		required=False,
		constraint=checkEmailAddress)

IRestrictedUserProfile['password_recovery_email_hash'].setTaggedValue( TAG_HIDDEN_IN_UI, True )
IRestrictedUserProfile['password_recovery_email_hash'].setTaggedValue( TAG_READONLY_IN_UI, True )

class IRestrictedUserProfileWithContactEmail(IRestrictedUserProfile):
	"""
	A profile that adds a (temporary) contact email during the account setup
	process.
	"""

	contact_email = _ValidTextLine(
		title='Contact email',
		description=u"An email address to use to contact someone responsible for this accounts' user",
		required=False,
		constraint=checkEmailAddress)

IRestrictedUserProfileWithContactEmail['contact_email'].setTaggedValue( TAG_REQUIRED_IN_UI, True )

class ICompleteUserProfile(IRestrictedUserProfile):
	"""
	A complete user profile.
	"""

	email = _ValidTextLine(
		title='Email',
		description=u'An email address that can be used for communication.',
		required=False,
		constraint=checkEmailAddress)

	opt_in_email_communication = schema.Bool(
		title="Can we contact you by email?",
		required=False,
		default=False )

	home_page = schema.URI(
		title='Home page',
		description="The URL for your external home page, "
					  "if you have one.",
		required=False)

	description = schema.Text(
		title='Biography',
		description="A short overview of who you are and what you "
					  "do. Will be displayed on your author page, linked "
					  "from the items you create.",
		required=False)

	location = schema.TextLine(
		title='Location',
		description="Your location - either city and "
					  "country - or in a company setting, where "
					  "your office is located.",
		required=False)

	# TODO: This probably comes from a vocabulary, at least for some users
	affiliation = schema.TextLine(
		title='Affiliation',
		description="Your affiliation, such as school name",
		required=False)

ICompleteUserProfile['home_page'].setTaggedValue( TAG_HIDDEN_IN_UI, True )
ICompleteUserProfile['description'].setTaggedValue( TAG_HIDDEN_IN_UI, True )
ICompleteUserProfile['location'].setTaggedValue( TAG_HIDDEN_IN_UI, True )

class IEmailRequiredUserProfile(ICompleteUserProfile):
	"""
	A user profile that ensures the email is filled in.

	.. note:: This is temporary and will become an alias for :class:`ICompleteUserProfile`
		when tests are updated across the board to require email addresses.
	"""

	email = _ValidTextLine(
		title='Email',
		description=u'',
		required=True, # TODO: This should move up when ready
		constraint=checkEmailAddress)


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
