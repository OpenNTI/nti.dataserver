#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User related interfaces.

.. note:: Currently, the interfaces implemented in this package are spread across
    this module, and :mod:`nti.dataserver.interfaces`.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,no-self-argument,protected-access

import re
import codecs
import string
import pkg_resources

import six

from zope import component
from zope import interface

from zope.container.constraints import contains

from zope.container.interfaces import IContained
from zope.container.interfaces import IContainer

from zope.interface import Attribute
from zope.interface import Interface

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from zope.schema import URI

from z3c.password.interfaces import NoPassword
from z3c.password.interfaces import InvalidPassword

from z3c.schema.email import isValidMailAddress

from nti.base.interfaces import ICreated
from nti.base.interfaces import ITitledDescribed

from nti.coremetadata.interfaces import IIntIdIterable
from nti.coremetadata.interfaces import IShouldHaveTraversablePath

from nti.coremetadata.schema import ExtendedCompoundModeledContentBody

from nti.dataserver.interfaces import InvalidData
from nti.dataserver.interfaces import ILastModified
from nti.dataserver.interfaces import checkCannotBeBlank
from nti.dataserver.interfaces import FieldCannotBeOnlyWhitespace

from nti.dataserver.users import MessageFactory as _

from nti.i18n.locales.interfaces import ICcTLDInformation

from nti.mailer.interfaces import IEmailAddressable

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import Date
from nti.schema.field import Dict
from nti.schema.field import Object
from nti.schema.field import HTTPURL
from nti.schema.field import Variant
from nti.schema.field import TextLine
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import ValidURI
from nti.schema.field import ValidBytesLine
from nti.schema.field import ValidDatetime
from nti.schema.field import DecodingValidTextLine

from nti.schema.interfaces import InvalidValue

from nti.schema.jsonschema import TAG_UI_TYPE
from nti.schema.jsonschema import TAG_HIDDEN_IN_UI
from nti.schema.jsonschema import TAG_READONLY_IN_UI
from nti.schema.jsonschema import TAG_REQUIRED_IN_UI


class UsernameCannotBeBlank(FieldCannotBeOnlyWhitespace):

    i18n_message = _(u"The username cannot be blank.")

    def __init__(self, username):
        super(UsernameCannotBeBlank, self).__init__('Username', username)


class UsernameContainsIllegalChar(InvalidData):

    def __init__(self, username, allowed_chars):
        self.username = username
        allowed_chars = set(allowed_chars) - set(string.letters + string.digits)
        allowed_chars = u''.join(sorted(allowed_chars))
        self.allowed_chars = allowed_chars
        if not allowed_chars:
            allowed_chars = u'no special characters'
        self.i18n_message = _(
            u'Username contains an illegal character. Only letters, digits, '
            u'and ${allowed_chars} are allowed.',
            mapping={'allowed_chars': allowed_chars}
        )

        super(UsernameContainsIllegalChar, self).__init__(self.i18n_message, 'Username',
                                                          username, value=username)

    def new_instance_restricting_chars(self, restricted_chars):
        allowed_chars = set(self.allowed_chars) - set(restricted_chars)
        return type(self)(self.username, allowed_chars)


class EmailAddressInvalid(InvalidData):
    """
    Invalid email address.
    """

    field = 'email'
    i18n_message = _(u"The email address you have entered is not valid.")

    def __init__(self, address):
        super(EmailAddressInvalid, self).__init__(address, value=address)


class RealnameInvalid(InvalidData):
    """
    Invalid realname.
    """

    field = 'realname'
    i18n_message = _(u"The first or last name you have entered is not valid.")

    def __init__(self, name):
        super(RealnameInvalid, self).__init__(name, value=name)


class BlankHumanNameError(RealnameInvalid):

    def __init__(self, name=u''):  # pylint: disable=useless-super-delegation
        super(BlankHumanNameError, self).__init__(name)


class OldPasswordDoesNotMatchCurrentPassword(InvalidPassword):
    i18n_message = _(
        u"The password you supplied does not match the current password.")


class PasswordCannotConsistOfOnlyWhitespace(NoPassword):
    i18n_message = _(
        u"Your pasword cannot contain only whitespace. Please try again.")


class InsecurePasswordIsForbidden(InvalidPassword):

    i18n_message = _(u"The password you supplied has been identified by security "
                     u"researchers as commonly used and insecure. Please try again.")

    def __init__(self, value=None):
        super(InsecurePasswordIsForbidden, self).__init__()
        if value:
            self.value = value
resource_stream = getattr(pkg_resources, 'resource_stream')


def _load_resource(n, f):
    stream = resource_stream(n, f)
    reader = codecs.getreader('utf-8')(stream)
    domains = set()
    for line in reader:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = line.upper()
        domains.add(line)
    return domains


# 2012-12-07: This list of passwords, identified by industry researchers,
# as extremely common and in all the rainbow tables, etc, is forbidden
# see http://arstechnica.com/gadgets/2012/12/blackberry-has-had-it-up-to-here-with-your-terrible-passwords/
# see https://github.com/typhoon2099/PasswordBannedList/blob/master/banned.list
_VERBOTEN_PASSWORDS = _load_resource(__name__, 'verboten-passwords.txt')
del _load_resource


def _checkEmailAddress(address):
    """
    Check email address.

    This should catch most invalid but no valid addresses.
    """
    result = False
    if isValidMailAddress(address):
        cctlds = component.getUtility(ICcTLDInformation)
        domain = address.rsplit('.', 1)[-1]
        result = domain.lower() in cctlds.getAvailableTLDs()
    return result


def _isValidEmail(email):
    """
    checks for valid email
    """
    return _checkEmailAddress(email)


def checkEmailAddress(value):
    return value and _isValidEmail(value)


#: A sequence of only non-alphanumeric characters
#: or a sequence of only digits and spaces, the underscore, and non-alphanumeric characters
#: (which is basically \W with digits and _ added back
_INVALID_REALNAME_RE = re.compile(r'^\W+$|^[\d\s\W_]+$', re.UNICODE)


def checkRealname(value):
    """
    Ensure that the realname doesn't consist of just digits/spaces
    or just alphanumeric characters
    """
    if value:
        if _INVALID_REALNAME_RE.match(value):
            raise RealnameInvalid(value)
        # Component parts? TODO: What about 'Jon Smith 3' as 'Jon Smith III'?
        # for x in value.split():
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

    ext_value = Attribute(u"The external value that will drive the update")
    meta_data = Attribute(u"A dictionary with update meta data")


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
    ext_value = Attribute(
        u"If the entity was created with external data, this will be it.")

    meta_data = Attribute(u"A dictionary with creation meta data")

    preflight_only = Attribute(
        u"A boolean, set to true if this is a preflight-only event.")


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
    ext_value = Attribute(u"External update data")


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
    pass


class IGoogleUserCreatedEvent(IObjectEvent):
    """
    Fired after an Google user has been created
    """
    request = Attribute(u"Request")


@interface.implementer(IGoogleUserCreatedEvent)
class GoogleUserCreatedEvent(ObjectEvent):

    def __init__(self, obj, request=None):
        super(GoogleUserCreatedEvent, self).__init__(obj)
        self.request = request


class IOpenIDUserCreatedEvent(IObjectEvent):
    """
    Fired after an OpenID user has been created
    """
    idurl = Attribute(u"The URL identifying the user on the external system")

    content_roles = Attribute(
        u"An iterable of strings naming provider-local content roles")


@interface.implementer(IOpenIDUserCreatedEvent)
class OpenIDUserCreatedEvent(ObjectEvent):

    def __init__(self, obj, idurl=None, content_roles=()):
        super(OpenIDUserCreatedEvent, self).__init__(obj)
        self.idurl = idurl
        self.content_roles = content_roles or ()


class IAvatarURLProvider(Interface):
    """
    Something that can provide a display URL. This is separate
    from the profile hierarchy to allow delegation of adapters.
    """

    avatarURL = URI(title=u"URL of your avatar picture",
                    description=u"If not provided, one will be generated for you.",
                    required=False)


class IBackgroundURLProvider(Interface):
    """
    Something that can provide a background URL. This is separate
    from the profile hierarchy to allow delegation of adapters.
    """

    backgroundURL = URI(title=u"URL of your background picture",
                        description=u"If not provided, one will be generated for you.",
                        required=False)


class IAvatarURL(Interface):
    """
    Something that features a display URL.
    """

    avatarURL = URI(title=u"URL of your avatar picture",
                    description=u"If not provided, one will be generated for you.",
                    required=False)
# Relax this constraint for the sake of BWC
IAvatarURL['avatarURL']._type = (str, six.text_type)


class IBackgroundURL(Interface):

    backgroundURL = URI(title=u"URL of your background picture",
                        description=u"If not provided, one will be generated for you.",
                        required=False)


# Relax this constraint for the sake of BWC
IBackgroundURL['backgroundURL']._type = (str, six.text_type)


class IProfileAvatarURL(IAvatarURL, IBackgroundURL):
    pass


class IAvatarChoices(Interface):
    """
    Something that can provide choices for possible avatar URLs.
    Typically this will be registered as an adapter from a string (the username/email)
    or the IUser object. It may named for the site.
    """

    def get_choices():
        """
        Returns a sequence of string choices.
        """


class IFriendlyNamed(Interface):

    alias = TextLine(title=u'Display name',
                     description=u"Your display name",
                     required=False)

    realname = TextLine(title=u'Your name',
                        description=u"Your full name",
                        required=False,
                        constraint=checkRealname)

    def get_searchable_realname_parts():
        """
        Return an iterable of the parsed non-empty parts of the realname,
        excluding such things as title and suffix (things typically not
        helpful in search results).
        """
IFriendlyNamed['realname'].setTaggedValue(TAG_REQUIRED_IN_UI, True)


class IImmutableFriendlyNamed(Interface):
    """
    Apply this to a context object to mark that it should not allow mutation
    of the friendly name values.
    """

    alias = TextLine(title=u'Display name',
                     description=u"Your display name",
                     required=False,
                     readonly=True)

    realname = TextLine(title=u'Your Name',
                        description=u"Your full name",
                        required=False,
                        readonly=True,
                        constraint=checkRealname)


class IRequireProfileUpdate(Interface):
    """
    Apply this as a marker to a context object (user) that requires a profile
    update. This will trigger profile validation (which usually doesn't happen)
    and allow bypassing certain parts of :class:`IImmutableFriendlyNamed.`
    """


class IEntityProfile(IFriendlyNamed, IProfileAvatarURL):
    """
    Base class that user/entity profiles should extend.
    """
IUserProfile = IEntityProfile  # alias for BWC


class IAddress(Interface):

    full_name = ValidTextLine(title=u"First name", required=True)

    street_address_1 = ValidTextLine(title=u"Street line 1",
                                     max_length=75, required=True)

    street_address_2 = ValidTextLine(title=u"Street line 2",
                                     required=False, max_length=75)

    city = ValidTextLine(title=u"City name", required=True)

    state = ValidTextLine(title=u"State name",
                          required=False, max_length=10)

    postal_code = ValidTextLine(title=u"Postal code",
                                required=False, max_length=30)

    country = ValidTextLine(title=u"Nation name", required=True)


class IUserContactProfile(Interface):

    addresses = Dict(title=u"A mapping of address objects.",
                     key_type=DecodingValidTextLine(title=u"Adresss key"),
                     value_type=Object(IAddress),
                     min_length=0,
                     required=False)

    phones = Dict(title=u"A mapping of address objects.",
                  key_type=DecodingValidTextLine(title=u"Phone key"),
                  value_type=ValidTextLine(title=u"A phone"),
                  min_length=0,
                  required=False)

    contact_emails = Dict(title=u"A mapping of contact emails.",
                          key_type=DecodingValidTextLine(title=u"Email key"),
                          value_type=ValidTextLine(title=u'Email',
                                                   constraint=checkEmailAddress),
                          min_length=0,
                          required=False)

from nti.schema.jsonschema import UI_TYPE_EMAIL
from nti.schema.jsonschema import UI_TYPE_HASHED_EMAIL


class IRestrictedUserProfile(IUserProfile):
    """
    A profile for a restricted user.
    """

    birthdate = Date(title=u'birthdate',
                     description=u'Your date of birth. '
                     u'If one is not provided, you will be assumed to be underage.',
                     required=False)

    password_recovery_email_hash = ValidTextLine(
        title=u"A secure hash of an email address used during password recovery",
        description=u"Typically auto-generated by setting the `email` field.",
        required=False)
    password_recovery_email_hash.setTaggedValue(TAG_HIDDEN_IN_UI, True)
    password_recovery_email_hash.setTaggedValue(TAG_READONLY_IN_UI, True)
    password_recovery_email_hash.setTaggedValue(TAG_UI_TYPE, UI_TYPE_HASHED_EMAIL)

    email = ValidTextLine(title=u'Email',
                          description=u'Email is not stored at this level, but the field is '
                          u'specified here as a convenient way'
                          u' to be able to set the password_recovery_email_hash',
                          required=False,
                          constraint=checkEmailAddress)
    email.setTaggedValue(TAG_UI_TYPE, UI_TYPE_HASHED_EMAIL)

    email_verified = Bool(title=u"Has the email been verified?",
                          required=False,
                          default=False)
    email_verified.setTaggedValue(TAG_HIDDEN_IN_UI, True)
    email_verified.setTaggedValue(TAG_READONLY_IN_UI, True)


class IRestrictedUserProfileWithContactEmail(IRestrictedUserProfile):
    """
    A profile that adds a (temporary) contact email during the account setup
    process.
    """

    contact_email = ValidTextLine(title=u'Contact email',
                                  description=u"An email address to use to contact someone "
                                  u"responsible for this accounts' user",
                                  required=False,
                                  constraint=checkEmailAddress)
    contact_email.setTaggedValue(TAG_REQUIRED_IN_UI, True)
    contact_email.setTaggedValue(TAG_UI_TYPE, UI_TYPE_EMAIL)


class IContactEmailRecovery(Interface):
    """
    Information used for recovering/resending consent emails to
    COPPA users, since we cannot actually retain the contact email.
    Should be registered as an adapter on the user.
    """
    contact_email_recovery_hash = Attribute(
        u"A string giving the hash of the contact email.")

    consent_email_last_sent = Attribute(
        u"A float giving the time the last consent email was sent.")


class ISocialMediaProfile(Interface):
    """
    A social media profile
    """

    facebook = ValidURI(title=u'Facebook',
                        description=u'Facebook URL',
                        required=False)

    twitter = ValidURI(title=u'Twitter',
                       description=u'Twitter URL',
                       required=False)

    googlePlus = ValidURI(title=u'GooglePlus',
                          description=u'GooglePlus URL',
                          required=False)

    linkedIn = ValidURI(title=u'LinkedIn',
                        description=u'LinkedIn URL',
                        required=False)

    instagram = ValidURI(title=u'Instagram',
                         description=u'Instagram URL',
                         required=False)


class IEducation(Interface):

    school = ValidTextLine(title=u'School name',
                           description=u'School name.',
                           required=True,
                           min_length=1)

    # TODO: Hardcoding max and min values for now, but
    # need to implement a proper validation in a view
    # where we verify that startYear <= endYear and that
    # the numbers are reasonable values for years.
    startYear = Int(title=u'Start year',
                    description=u'Start year',
                    required=False)

    endYear = Int(title=u'End year',
                  description=u'End year',
                  required=False)

    expected_graduation = ValidDatetime(title=u"The expected graduation date",
                                        default=None,
                                        required=False)

    degree = ValidTextLine(title=u'Degree name',
                           description=u'Degree name',
                           required=False)

    description = ValidText(title=u'Degree description',
                            description=u'Degree description',
                            required=False)


class IEducationProfile(Interface):
    """
    An education profile
    """

    education = ListOrTuple(Object(IEducation, title=u"The education entry"),
                            title=u"Education entries",
                            required=False,
                            min_length=0)


class IProfessionalPosition(Interface):

    companyName = ValidTextLine(title=u'Company name',
                                description=u'CompanyName name.',
                                required=True,
                                min_length=1)

    title = ValidTextLine(title=u'Title',
                          description=u'Title',
                          required=False)

    # TODO: As with IEducation, need to do startYear <= endYear
    # validation in a view.
    startYear = Int(title=u'Start year',
                    description=u'Start year',
                    required=False)

    endYear = Int(title=u'End year',
                  description=u'End year',
                  required=False)

    description = ValidText(title=u'Position description',
                            description=u'Position description',
                            required=False)


IPosition = IProfessionalPosition


class IProfessionalProfile(Interface):
    """
    A professional profile
    """

    positions = ListOrTuple(Object(IProfessionalPosition, title=u"The profesional position entry"),
                            title=u"professional position entries",
                            required=False,
                            min_length=0)


class IInterestProfile(Interface):
    """
    A Interest profile
    """

    interests = ListOrTuple(ValidTextLine(title=u"An interest"),
                            title=u"interest entries",
                            required=False,
                            min_length=0)


class IAboutProfile(Interface):

    about = Variant((ValidText(title=u'About',
                               description=u"A description of a user",
                               required=False,
                               constraint=checkCannotBeBlank),
                     ExtendedCompoundModeledContentBody()),
                    description=u"A simple overview",
                    required=False)
    about.__name__ = 'about'


class ICompleteUserProfile(IRestrictedUserProfile,
                           IEmailAddressable,
                           ISocialMediaProfile,
                           IEducationProfile,
                           IProfessionalProfile,
                           IInterestProfile,
                           IAboutProfile,
                           IUserContactProfile):
    """
    A complete user profile.
    """

    email = ValidTextLine(title=u'Email',
                          description=u'An email address that can be used for communication.',
                          required=False,
                          constraint=checkEmailAddress)
    email.setTaggedValue(TAG_UI_TYPE, UI_TYPE_EMAIL)

    opt_in_email_communication = Bool(title=u"Can we contact you by email?",
                                      required=False,
                                      default=False)

    home_page = HTTPURL(title=u'Home page',
                        description=u"Your home page",
                        required=False)

    description = ValidText(title=u'Biography',
                            description=u"A short overview of who you are and what you "
                            u"do. Will be displayed on your author page, linked "
                                        u"from the items you create.",
                            max_length=140,  # twitter
                                        required=False,
                            constraint=checkCannotBeBlank)

    location = ValidTextLine(title=u'Location',
                             description=u"Your location (or in a company setting, where "
                             u"your office is located)",
                             required=False,
                             constraint=checkCannotBeBlank)

    affiliation = ValidTextLine(title=u'Affiliation',
                                description=u"Your affiliation, such as school name",
                                max_length=140,
                                required=False,
                                constraint=checkCannotBeBlank)

    role = ValidTextLine(title=u'Role',
                         description=u"Your role",
                         max_length=140,
                         required=False,
                         constraint=checkCannotBeBlank)


class IEmailRequiredUserProfile(ICompleteUserProfile):
    """
    A user profile that ensures the email is filled in.

    .. note:: This is temporary and will become an alias for :class:`ICompleteUserProfile`
            when tests are updated across the board to require email addresses.
    """

    email = ValidTextLine(title=u'Email',
                          description=u'',
                          required=True,
                          constraint=checkEmailAddress)
    email.setTaggedValue(TAG_UI_TYPE, UI_TYPE_EMAIL)


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


class IAccountProfileSchemafier(Interface):
    """
    Usually registered as an adapter from a IUser interface or sometimes an IEntity.

    Handles generating the profile schema.
    """

    def make_schema():
        """
        :return: the externalized profile schema
        """


@interface.implementer(IUserProfileSchemaProvider)
class FriendlyNamedSchemaProvider(object):
    """
    Return the base IFriendlyNamed profile. This will work as an
    adapter for anything that extends Entity, and the most derived available
    profile will be used (that is registered as an adapter for that type).
    """

    def __init__(self, context):
        pass

    def getSchema(self):
        return IFriendlyNamed


class ICommunitySchema(IFriendlyNamed, IAboutProfile):
    pass


class ICommunityProfile(IUserProfile, ICommunitySchema):
    pass


ICommunityProfile['avatarURL']._type = (str, six.text_type)  # relax
ICommunityProfile['backgroundURL']._type = (str, six.text_type)  # relax


@interface.implementer(IUserProfileSchemaProvider)
class CommunitySchemaProvider(object):

    def __init__(self, context):
        pass

    def getSchema(self):
        return ICommunitySchema


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


def validateAccept(value):
    if not value == True:
        return False
    return True


# Membership.


class IDisallowActivityLink(Interface):
    """
    marker interface to disallow activity link
    """


class IDisallowMembersLink(Interface):
    """
    marker interface to disallow members link
    """


class IDisallowHiddenMembership(Interface):
    """
    marker interface to disallow hidden memberships
    """


class IDisallowSuggestedContacts(Interface):
    """
    marker interface to disallow suggested contacts
    """


class IDisallowMembershipOperations(IDisallowMembersLink,
                                    IDisallowActivityLink,
                                    IDisallowHiddenMembership,
                                    IDisallowSuggestedContacts):
    pass


class IHiddenMembership(IIntIdIterable):

    def hide(entity):
        """
        hide the memebership for the specified entity
        """

    def unhide(self, entity):
        """
        unhide the memebership for the specified entity
        """

    def number_of_members():
        """
        Return the number of members in this object
        """

    def __contains__(entity):
        """
        check if membership of the specifed entity is hidden
        """

# suggested contacts.


class ISuggestedContactRankingPolicy(Interface):
    """
    Defines a user ranking policy for a provider. This policy
    defines the order in which the suggestions are returned
    """

    priority = Int(title=u"Provider prority", required=False, default=1)

    def sort(contacts):
        """
        sort the specified suggested contacts
        """


class ISuggestedContactsProvider(Interface):

    """
    Defines a utility that allows to return contact suggestions for a user
    """

    ranking = Object(ISuggestedContactRankingPolicy, title=u"Ranking policy",
                     required=False)

    context = Object(Interface, title=u"Provider context",
                     required=False)

    def suggestions(user, source_user=None):
        """
        Return a iterator with suggested contacts ordered by the ranking policy.
        Optionally, give a source_user to return targeted suggestions.
        """


class ISecondOrderSuggestedContactProvider(ISuggestedContactsProvider):

    """
    Defines a utility that allows to return second order contact suggestions.
    """


class ISuggestedContact(Interface):
    username = ValidTextLine(title=u"username", required=True)
    rank = Int(title=u"contact rank", required=False, default=1)


def get_all_suggested_contacts(user):
    """
    Scan all registered ISuggestedContactsProvider and return their suggestions
    """
    for _, provider in list(component.getUtilitiesFor(ISuggestedContactsProvider)):
        for suggestion in provider.suggestions(user):
            suggestion.provider = provider
            yield suggestion


class IUsernameGeneratorUtility(Interface):
    """
    Utility to generate a guaranteed unique username. By default, this username
    is opaque.
    """

    def generate_username():
        """
        Return the guaranteed unique username.
        """


class IUserUpdateUtility(Interface):
    """
    Adapter utility with various functions useful when updating a user. This typically
    is a third-party updating another user.
    """

    def can_update_user(target_user):
        """
        Returns whether a user can update the `target_user`. This is useful to
        ensure admins of one site do not edit users from another site in a
        shared environment.
        """


class IUpsertUserPreCreateEvent(IObjectEvent):
    """
    Fired before a user has been created via UserUpsert.
    """


@interface.implementer(IUpsertUserPreCreateEvent)
class UpsertUserPreCreateEvent(ObjectEvent):

    def __init__(self, request): # pylint: disable=useless-super-delegation
        super(UpsertUserPreCreateEvent, self).__init__(request)


class IUpsertUserCreatedEvent(IObjectEvent):
    """
    Fired after a user has been created via UserUpsert.
    """
    request = Attribute(u"Request")


@interface.implementer(IUpsertUserCreatedEvent)
class UpsertUserCreatedEvent(ObjectEvent):

    def __init__(self, obj, request=None):
        super(UpsertUserCreatedEvent, self).__init__(obj)
        self.request = request


# index

from nti.coremetadata.interfaces import UserLastSeenEvent
from nti.coremetadata.interfaces import IUserLastSeenEvent

UserLastSeenEvent = UserLastSeenEvent
IUserLastSeenEvent = IUserLastSeenEvent


class IDisplayNameAdapter(Interface):
    """
    Interface for an index adapter to get an entity display name
    """
    displayname = Attribute(u"Display name")


class IUIReadOnlyProfileSchema(interface.Interface):
    """
    A marker interface for user profiles that should be read only when schemafied externally
    """


class IUserToken(ICreated, ILastModified, ITitledDescribed, IContained):
    """
    User token objects.
    """

    key = ValidBytesLine(title=u"The token key",
                         required=True)

    title = ValidTextLine(title=u"Title of the token",
                          default=u'',
                          required=False)

    description = ValidTextLine(title=u"Description of the token",
                                required=False)

    scopes = ListOrTuple(ValidTextLine(title=u"The scope of the token",
                                       description=u"Some token views may restrict access to appropriately scoped tokens."),
                        title=u"scopes",
                        required=False,
                        min_length=0)


class IUserTokenContainer(IShouldHaveTraversablePath,
                          ILastModified,
                          IContainer):
    """
    A storage container for :class:`IUserToken` objects.
    """
    contains(IUserToken)

    def store_token(token):
        """
        Store the token in the container.
        """

    def get_all_tokens_by_scope(scope):
        """
        Finds all tokens described by the given scope, or None.
        """
