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
import re


from zope.i18n import translate
from . import MessageFactory as _



class _InvalidData(zope.schema.interfaces.InvalidValue):
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

	i18n_message = 'Username cannot be blank'

	def __init__( self, username ):
		super(UsernameCannotBeBlank,self).__init__( self.i18n_message, 'Username', username )

class UsernameContainsIllegalChar(_InvalidData):

	def __init__( self, username, allowed_chars ):
		self.i18n_message = _(
			'Username contains an illegal character. Only "${allowed_chars}" are allowed.',
			mapping={'allowed_chars': allowed_chars})

		super(UsernameContainsIllegalChar,self).__init__( self.i18n_message, 'Username', username )

class EmailAddressInvalid(_InvalidData):
	"""Invalid email address."""

	i18n_message = "The email address you have entered is not valid"

	def __init__( self, address ):
		super(EmailAddressInvalid,self).__init__( address )


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

@interface.implementer(IWillUpdateNewEntityEvent)
class WillUpdateNewEntityEvent(zope.component.interfaces.ObjectEvent):
	pass

class IAvatarURL(Interface):
	"""
	Something that features a display URL.
	"""

	avatarURL = schema.URI(
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

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

import nti.utils.schema
class _ValidTextLine(nti.utils.schema.FieldValidationMixin,schema.TextLine):
	pass

class ICompleteUserProfile(IFriendlyNamed):
	"""
	A complete user profile.
	"""

	email = _ValidTextLine(
		title='Email',
		description=u'',
		required=False, # TODO: Should be true when the tests are ready
		constraint=checkEmailAddress)

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



	birthdate = schema.Date(
		title='birthdate',
		description='Your date of birth',
		required=False )

	# TODO: This probably comes from a vocabulary, at least for some users
	affiliation = schema.TextLine(
		title='Affiliation',
		description="Your affiliation, such as school name",
		required=False)

class IEmailRequiredUserProfile(ICompleteUserProfile):
	"""
	A user profile that ensures the email is filled in.

	.. note:: This is temporary and will become an alias for :class:`ICompleteUserProfile`
		when tests are updated across the board to require email addresses.
	"""

	email = _ValidTextLine(
		title='Email',
		description=u'',
		required=True, # TODO: Should be true when the tests are ready
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

# class IEnhancedUserDataSchema(IUserDataSchema):
# 	""" Use all the fields from the default user data schema, and add various
# 	extra fields.
# 	"""
# 	firstname = schema.TextLine(
# 		title=_(u'label_firstname', default=u'First name'),
# 		description=_(u'help_firstname',
# 					  default=u"Fill in your given name."),
# 		required=False,
# 		)
# 	lastname = schema.TextLine(
# 		title=_(u'label_lastname', default=u'Last name'),
# 		description=_(u'help_lastname',
# 					  default=u"Fill in your surname or your family name."),
# 		required=False,
# 		)
# 	gender = schema.Choice(
# 		title=_(u'label_gender', default=u'Gender'),
# 		description=_(u'help_gender',
# 					  default=u"Are you a girl or a boy?"),
# 		values = [
# 			_(u'Male'),
# 			_(u'Female'),
# 			],
# 		required=True,
# 		)
# 	birthdate = schema.Date(
# 		title=_(u'label_birthdate', default=u'birthdate'),
# 		description=_(u'help_birthdate',
# 			default=u'Your date of birth, in the format dd-mm-yyyy'),
# 		required=False,
# 		)
# 	city = schema.TextLine(
# 		title=_(u'label_city', default=u'City'),
# 		description=_(u'help_city',
# 					  default=u"Fill in the city you live in."),
# 		required=False,
# 		)
# 	country = schema.TextLine(
# 		title=_(u'label_country', default=u'Country'),
# 		description=_(u'help_country',
# 					  default=u"Fill in the country you live in."),
# 		required=False,
# 		)
# 	phone = schema.TextLine(
# 		title=_(u'label_phone', default=u'Telephone number'),
# 		description=_(u'help_phone',
# 					  default=u"Leave your phone number so we can reach you."),
# 		required=False,
# 		)
# 	newsletter = schema.Bool(
# 		title=_(u'label_newsletter', default=u'Subscribe to newsletter'),
# 		description=_(u'help_newsletter',
# 					  default=u"If you tick this box, we'll subscribe you to "
# 						"our newsletter."),
# 		required=False,
# 		)
# 	accept = schema.Bool(
# 		title=_(u'label_accept', default=u'Accept terms of use'),
# 		description=_(u'help_accept',
# 					  default=u"Tick this box to indicate that you have found,"
# 					  " read and accepted the terms of use for this site. "),
# 		required=True,
# 		constraint=validateAccept,
# 		)
