#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of user profile related storage.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import hashlib
import nameparser

from zope import component
from zope import interface

from zope.annotation import factory as afactory

from zope.cachedescriptors.property import CachedProperty

from zope.location.interfaces import ILocation

from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from persistent import Persistent

from nti.common.nameparser import constants as np_constants
from nti.common.nameparser import all_prefixes as np_all_prefixes

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IPrincipal

from nti.dataserver.users.interfaces import IAddress
from nti.dataserver.users.interfaces import IEducation
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IAboutProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IInterestProfile
from nti.dataserver.users.interfaces import ICommunityProfile
from nti.dataserver.users.interfaces import IEducationProfile
from nti.dataserver.users.interfaces import IEmailAddressable
from nti.dataserver.users.interfaces import ISocialMediaProfile
from nti.dataserver.users.interfaces import IUserContactProfile
from nti.dataserver.users.interfaces import ICompleteUserProfile
from nti.dataserver.users.interfaces import IProfessionalProfile
from nti.dataserver.users.interfaces import IProfessionalPosition
from nti.dataserver.users.interfaces import IRestrictedUserProfile
from nti.dataserver.users.interfaces import IEmailRequiredUserProfile
from nti.dataserver.users.interfaces import IRestrictedUserProfileWithContactEmail

from nti.dataserver.users.utils import AvatarUrlProperty as _AvatarUrlProperty
from nti.dataserver.users.utils import BackgroundUrlProperty as _BackgroundUrlProperty
from nti.dataserver.users.utils import BlurredAvatarUrlProperty as _BlurredAvatarUrlProperty

from nti.externalization import update_from_external_object

from nti.externalization.representation import WithRepr

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

logger = __import__('logging').getLogger(__name__)


class _ExistingDictReadFieldPropertyStoredThroughField(FP):
    """
    Migration from existing data fields in instance dictionaries to
    our profile storage. There are probably few enough of these in places we care
    about to be almost unnecessary.
    """

    _existing_name = None

    def __init__(self, field, name=None, exist_name=None):
        super(_ExistingDictReadFieldPropertyStoredThroughField, self).__init__(field, name=name)
        if exist_name:
            self._existing_name = exist_name

    def getValue(self, inst, field):
        ex_val = getattr(inst.context,
                         self._existing_name or 'This Value Cannot Be an Attr', None)
        if ex_val:
            return ex_val
        return super(_ExistingDictReadFieldPropertyStoredThroughField, self).getValue(inst, field)

    def setValue(self, inst, field, value):
        try:
            del inst.context.__dict__[self._existing_name]
        except KeyError:
            pass
        super(_ExistingDictReadFieldPropertyStoredThroughField, self).setValue(inst, field, value)

        # We're not implementing the queryValue method, which is used
        # somehow when the field is readonly and...something
        # We don't use this for readonly fields, so we don't care
_EDRFP = _ExistingDictReadFieldPropertyStoredThroughField

# The profile classes use schema fields to define what can be stored
# and to perform validation. The schema fields are handled dynamically with the
# fieldproperty classes, and are added to the classes themselves
# dynamically in _init

# Isn't this extremely similar to dm.zope.schema? Did we forget
# about that?


def get_searchable_realname_parts(realname):
    # This implementation is fairly naive, returning
    # first, middle, and last if they are not blank. How does
    # this handle more complex naming scenarios?
    if realname:
        # CFA: another suffix we see from certain financial quorters
        name = nameparser.HumanName(realname,
                                    constants=np_constants(extra_suffixes=('cfa',)))
        # We try to be a bit more sophisticated around certain
        # naming scenarios.
        if name.first == realname and ' ' in realname:
            # It failed to parse. We've seen this with names like 'Di Lu',
            # where 'Di' is in the prefix list as a common component
            # of European last names. Take out any prefixes that match the components
            # of this name and try again (avoid doing this if there are simply
            # no components, as can happen on the mathcounts site or in tests)
            splits = realname.lower().split()
            prefixes = np_all_prefixes().symmetric_difference(splits)
            constants = np_constants(prefixes=prefixes,
                                     extra_suffixes=('cfa',))
            name = nameparser.HumanName(realname, constants=constants)
        # because we are cached, be sure to return an immutable value
        return tuple([x for x in name[1:4] if x])


@component.adapter(IEntity)
@interface.implementer(IFriendlyNamed, ILocation)
class FriendlyNamed(Persistent):
    """
    An adapter for storing naming data for users. Intended to be an
    annotation, used with an annotation factory; in that scenario, the
    "context" of the annotation is actually the ``__parent__`` (as set
    by the factory). However, for ease of testing, we can also
    explicitly accept the context as an optional argument to the
    constructor.
    """

    __name__ = None
    __parent__ = None

    def __init__(self, context=None):
        super(FriendlyNamed, self).__init__()
        if context:
            self.__parent__ = context

    @property
    def context(self):
        return self.__parent__

    @CachedProperty('realname')
    def _searchable_realname_parts(self):
        result = get_searchable_realname_parts(self.realname)
        # Returning none keeps the entity out of the index
        return result

    def get_searchable_realname_parts(self):
        return self._searchable_realname_parts


class ImageProfileMixin(object):
    """
    An adapter for storing profile information. We provide a specific implementation
    of the ``avatarURL`` and 'backgroundURL' properties rather than relying on field
    storage.

    For convenience, we have a read-only shadow of the username value.
    """
    #: NOTE: See users_external, this is fairly tightly coupled to that

    _avatarURL = None
    avatarURL = _AvatarUrlProperty(data_name="avatarURL",
                                   url_attr_name='_avatarURL',
                                   file_attr_name='_avatarURL')

    __getitem__ = avatarURL.make_getitem()

    _blurredAvatarURL = None
    blurredAvatarURL = _BlurredAvatarUrlProperty(data_name="blurredAvatarURL",
                                                 url_attr_name='_blurredAvatarURL',
                                                 file_attr_name='_blurredAvatarURL')

    _backgroundURL = None
    backgroundURL = _BackgroundUrlProperty(data_name="backgroundURL",
                                           url_attr_name='_backgroundURL',
                                           file_attr_name='_backgroundURL')


@component.adapter(IUser)
@interface.implementer(IUserProfile)
class UserProfile(FriendlyNamed, ImageProfileMixin):
    username = property(lambda self: self.context.username)


@component.adapter(ICommunity)
@interface.implementer(ICommunityProfile)
class CommunityProfile(FriendlyNamed, ImageProfileMixin):
    about = FP(ICommunityProfile['about'])
    username = property(lambda self: self.context.username)


@component.adapter(IUserProfile)
@interface.implementer(IPrincipal)
def _profile_to_principal(profile):
    return IPrincipal(profile.context)


def make_password_recovery_email_hash(email):
    if not email:
        raise ValueError("Must provide email")
    email = email.lower()  # ensure casing is consistent
    return unicode(hashlib.sha1(email).hexdigest())


@component.adapter(IUser)
@interface.implementer(IRestrictedUserProfile)
class RestrictedUserProfile(UserProfile):

    # 2/28/19 email_verified used to be explicitly set here.
    # This was removed so that a FieldProperty will be created
    # via `_init` instead to allow for subscriber hooks

    # If anyone tries to set an email on us, we turn it into the recovery hash
    email = property(lambda self: None,
                     lambda self, nv: setattr(self, 'password_recovery_email_hash',
                                              make_password_recovery_email_hash(nv)),
                     doc="This type of profile cannot store an actual email address."
                     "If anyone tries, it becomes the recovery hash")


@component.adapter(IUser)
@interface.implementer(IRestrictedUserProfileWithContactEmail)
class RestrictedUserProfileWithContactEmail(RestrictedUserProfile):
    pass

# We actually will want to register this in the same
# cases we register the profile itself, for the same kinds of users


@interface.implementer(IEmailAddressable)
@component.adapter(IRestrictedUserProfileWithContactEmail)
class RestrictedUserProfileWithContactEmailAddressable(object):

    def __init__(self, context):
        self.email = context.contact_email


@WithRepr
@interface.implementer(IEducation)
class Education(SchemaConfigured, Persistent):
    createDirectFieldProperties(IEducation)

    __external_class_name__ = "EducationalExperience"
    mime_type = mimeType = 'application/vnd.nextthought.profile.educationalexperience'


@WithRepr
@interface.implementer(IProfessionalPosition)
class ProfessionalPosition(SchemaConfigured, Persistent):
    createDirectFieldProperties(IProfessionalPosition)

    __external_class_name__ = "ProfessionalPosition"
    mime_type = mimeType = 'application/vnd.nextthought.profile.professionalposition'


@WithRepr
@interface.implementer(ISocialMediaProfile)
class SocialMediaProfile(SchemaConfigured, Persistent):
    createDirectFieldProperties(ISocialMediaProfile)

    facebook = FP(ISocialMediaProfile['facebook'])
    twitter = FP(ISocialMediaProfile['twitter'])
    linkedIn = FP(ISocialMediaProfile['linkedIn'])
    instagram = FP(ISocialMediaProfile['instagram'])


@WithRepr
@interface.implementer(IEducationProfile)
class EducationProfile(SchemaConfigured, Persistent):
    createDirectFieldProperties(IEducationProfile)

    education = FP(IEducationProfile['education'])


@WithRepr
@interface.implementer(IProfessionalProfile)
class ProfessionalProfile(SchemaConfigured, Persistent):
    createDirectFieldProperties(IProfessionalProfile)

    positions = FP(IProfessionalProfile['positions'])


@WithRepr
@interface.implementer(IInterestProfile)
class InterestProfile(SchemaConfigured, Persistent):
    createDirectFieldProperties(IInterestProfile)

    interests = FP(IInterestProfile['interests'])


@WithRepr
@interface.implementer(IAboutProfile)
class AboutProfile(SchemaConfigured, Persistent):
    createDirectFieldProperties(IAboutProfile)

    about = FP(IAboutProfile['about'])


@WithRepr
@interface.implementer(IAddress)
class Address(SchemaConfigured, Persistent):
    createDirectFieldProperties(IAddress)

    full_name = FP(IAddress['full_name'])
    street_address_1 = FP(IAddress['street_address_1'])
    street_address_2 = FP(IAddress['street_address_2'])
    city = FP(IAddress['city'])
    state = FP(IAddress['state'])
    postal_code = FP(IAddress['postal_code'])
    country = FP(IAddress['country'])


@interface.implementer(IAddress)
@component.adapter(dict)
def dict_to_address(addr_dict):
    new_addr = Address()
    update_from_external_object(new_addr, addr_dict)
    return new_addr


@WithRepr
@interface.implementer(IUserContactProfile)
class UserContactProfile(SchemaConfigured, Persistent):
    createDirectFieldProperties(IUserContactProfile)

    @property
    def mailing_address(self):
        return self.addresses.get('mailing_address') \
            or self.addresses.get('mailing')

    @property
    def billing_address(self):
        return self.addresses.get('billing_address') \
            or self.addresses.get('billing')

    @property
    def home_phone(self):
        return self.phones.get('home_phone') or self.phones.get('home')


    @property
    def work_phone(self):
        return self.phones.get('work_phone') or self.phones.get('work')



@component.adapter(IUser)
@interface.implementer(ICompleteUserProfile)
class CompleteUserProfile(RestrictedUserProfile,  # order matters
                          SocialMediaProfile,
                          InterestProfile,
                          EducationProfile,
                          AboutProfile,
                          UserContactProfile,
                          ProfessionalProfile):
    pass


@interface.implementer(IEmailRequiredUserProfile)
class EmailRequiredUserProfile(CompleteUserProfile):
    """
    An adapter for requiring the email.
    """


def add_profile_fields(iface, clazz, field_map=None):
    """
    Given an interfaces that extends :class:`nti.dataserver.users.interfaces.IUserProfile`
    and a class that extends :class:`nti.dataserver.users.user_profile.UserProfile`,
    add the fields necessary to implement the interface to the class's dictionary.

    :param field_map: If given, maps from schema fields to legacy storage that can be
            found on the adapted object. Generally not used outside of this module.

    :return: The object given as `clazz`.
    """

    for _x in iface.names():
        # Since the names are defined and may be overrides,
        # we also let overrides happen in the class dicts
        if not _x in clazz.__dict__:
            if field_map and _x in field_map:
                field = _EDRFP(iface[_x], exist_name=field_map[_x])
            else:
                field = FP(iface[_x])

            setattr(clazz, _x, field)

    return clazz


def _init():
    # Map "existing"/legacy User/Entity dict storage to their new profile field
    _field_map = {'alias': '_alias', 'realname': '_realname'}
    _class_map = {
        IUserProfile: UserProfile,
        IFriendlyNamed: FriendlyNamed,
        ICommunityProfile: CommunityProfile,
        ICompleteUserProfile: CompleteUserProfile,
        IRestrictedUserProfile: RestrictedUserProfile,
        IEmailRequiredUserProfile: EmailRequiredUserProfile,
        IRestrictedUserProfileWithContactEmail: RestrictedUserProfileWithContactEmail}

    for iface, clazz in _class_map.items():
        add_profile_fields(iface, clazz, field_map=_field_map)


_init()
del _init

FRIENDLY_NAME_KEY = 'nti.dataserver.users.user_profile.FriendlyNamed'
FriendlyNamedFactory = afactory(FriendlyNamed, key=FRIENDLY_NAME_KEY)

RestrictedUserProfileFactory = afactory(RestrictedUserProfile)
RestrictedUserProfileWithContactEmailFactory = afactory(RestrictedUserProfileWithContactEmail)

COMMUNITY_PROFILE_KEY = 'nti.dataserver.users.user_profile.CommunityProfile'
CommunityProfileFactory = afactory(CommunityProfile,
                                   key=COMMUNITY_PROFILE_KEY)

COMPLETE_USER_PROFILE_KEY = 'nti.dataserver.users.user_profile.CompleteUserProfile'
CompleteUserProfileFactory = afactory(CompleteUserProfile,
                                      key=COMPLETE_USER_PROFILE_KEY)

EMAIL_REQUIRED_USER_PROFILE_KEY = 'nti.dataserver.users.user_profile.EmailRequiredUserProfile'
EmailRequiredUserProfileFactory = afactory(EmailRequiredUserProfile,
                                           key=EMAIL_REQUIRED_USER_PROFILE_KEY)
