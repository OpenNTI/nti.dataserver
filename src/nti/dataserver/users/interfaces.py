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

from zope.interface import Interface
from zope import schema
import re



class EmailAddressInvalid(schema.ValidationError):
    '''Invalid email address.'''

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

def _isValidEmail(email):
	""" checks for valid email """
	if EMAIL_RE.search(email) == None:
		raise EmailAddressInvalid(email)

	_checkEmailAddress(email)


def checkEmailAddress(value):
	if value and _isValidEmail(value):
		return True

	raise EmailAddressInvalid( value )



class IUserDataSchema(Interface):

	fullname = schema.TextLine(
		title='Full Name',
		description="Enter full name, e.g. John Smith.",
		required=False)

	email = schema.ASCIILine(
		title='Email',
		description=u'',
		required=True,
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

	avatarURL = schema.URI(
		title="URL of your avatar picture",
		description="If not provided, one will be generated for you.",
		required=False )

	birthdate = schema.Date(
		title='birthdate',
		description='Your date of birth',
		required=False )

	# TODO: This probably comes from a vocabulary, at least for some users
	affiliation = schema.TextLine(
		title='Affiliation',
		description="Your affiliation, such as school name",
		required=False)

	# portrait = FileUpload(title=_(u'label_portrait', default=u'Portrait'),
	# 	description=_(u'help_portrait',
	# 				  default=u'To add or change the portrait: click the '
	# 				  '"Browse" button; select a picture of yourself. '
	# 				  'Recommended image size is 75 pixels wide by 100 '
	# 				  'pixels tall.'),
	# 	required=False)

	# pdelete = schema.Bool(
	# 	title=_(u'label_delete_portrait', default=u'Delete Portrait'),
	# 	description=u'',
	# 	required=False)

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
