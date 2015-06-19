#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of user profile related storage.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import hashlib
import nameparser

from zope import component
from zope import interface

from zope.annotation import factory as afactory

from zope.location.interfaces import ILocation

from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from persistent import Persistent

from nti.common.property import CachedProperty

from nti.externalization.representation import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from ..interfaces import IUser
from ..interfaces import IEntity
from ..interfaces import IPrincipal

from .interfaces import IEducation
from .interfaces import IUserProfile
from .interfaces import IFriendlyNamed
from .interfaces import IInterestProfile
from .interfaces import IEducationProfile
from .interfaces import IEmailAddressable
from .interfaces import ISocialMediaProfile
from .interfaces import ICompleteUserProfile
from .interfaces import IProfessionalProfile
from .interfaces import IProfessionalPosition
from .interfaces import IRestrictedUserProfile
from .interfaces import IEmailRequiredUserProfile
from .interfaces import IRestrictedUserProfileWithContactEmail

from .utils import AvatarUrlProperty as _AvatarUrlProperty
from .utils import BackgroundUrlProperty as _BackgrounUrlProperty

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

# The profile classes use schema fields to define what can be stored
# and to perform validation. The schema fields are handled dynamically with the
# fieldproperty classes, and are added to the classes themselves dynamically in _init

# TODO: Isn't this extremely similar to dm.zope.schema? Did we forget about that?

def get_searchable_realname_parts(realname):
	nameparser_config = getattr(nameparser, 'config')

	# This implementation is fairly naive, returning
	# first, middle, and last if they are not blank. How does
	# this handle more complex naming scenarios?
	if realname:
		# CFA: another suffix we see from certain financial quorters
		suffixes = nameparser_config.SUFFIXES | set(('cfa',))
		constants = nameparser_config.Constants(suffixes=suffixes)
		name = nameparser.HumanName(realname, constants=constants)
		# We try to be a bit more sophisticated around certain
		# naming scenarios.
		if name.first == realname and ' ' in realname:
			# It failed to parse. We've seen this with names like 'Di Lu',
			# where 'Di' is in the prefix list as a common component
			# of European last names. Take out any prefixes that match the components
			# of this name and try again (avoid doing this if there are simply
			# no components, as can happen on the mathcounts site or in tests)
			splits = realname.lower().split()
			prefixes = nameparser_config.PREFIXES.symmetric_difference(splits)
			constants = nameparser_config.Constants(prefixes=prefixes, suffixes=suffixes)
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

@component.adapter(IUser)
@interface.implementer(IUserProfile)
class UserProfile(FriendlyNamed):
	"""
	An adapter for storing profile information. We provide a specific implementation
	of the ``avatarURL`` property rather than relying on field storage.

	For convenience, we have a read-only shadow of the username value.
	"""
	# : NOTE: See users_external, this is fairly tightly coupled to that

	_avatarURL = None
	avatarURL = _AvatarUrlProperty(data_name="avatarURL",
								   url_attr_name='_avatarURL',
								   file_attr_name='_avatarURL')

	__getitem__ = avatarURL.make_getitem()

	_backgroundURL = None
	backgroundURL = _BackgrounUrlProperty(data_name="backgroundURL",
										  url_attr_name='_backgroundURL',
										  file_attr_name='_backgroundURL')

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
	email_verified = False

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

# XXX: We actually will want to register this in the same
# cases we register the profile itself, for the same kinds of users

@component.adapter(IRestrictedUserProfileWithContactEmail)
@interface.implementer(IEmailAddressable)
class RestrictedUserProfileWithContactEmailAddressable(object):

	def __init__(self, context):
		self.email = context.contact_email

@WithRepr
@interface.implementer(IEducation)
class Education(SchemaConfigured, Persistent):
	createDirectFieldProperties(IEducation)

	def __init__(self, *args, **kwargs):
		Persistent.__init__(self)
		SchemaConfigured.__init__(self, *args, **kwargs)
	
@WithRepr
@interface.implementer(IProfessionalPosition)
class ProfessionalPosition(SchemaConfigured, Persistent):
	createDirectFieldProperties(IProfessionalPosition)

	def __init__(self, *args, **kwargs):
		Persistent.__init__(self)
		SchemaConfigured.__init__(self, *args, **kwargs)

@WithRepr
@interface.implementer(ISocialMediaProfile)
class SocialMediaProfile(SchemaConfigured, Persistent):
	createDirectFieldProperties(ISocialMediaProfile)

	facebook = FP(ISocialMediaProfile['facebook'])
	twitter = FP(ISocialMediaProfile['twitter'])
	googlePlus = FP(ISocialMediaProfile['googlePlus'])
	linkedIn = FP(ISocialMediaProfile['linkedIn'])
	
@WithRepr
@interface.implementer(IEducationProfile)
class EducationProfile(SchemaConfigured, Persistent):
	createDirectFieldProperties(IEducationProfile)
	
	education =  FP(IEducationProfile['education'])
	
@WithRepr
@interface.implementer(IProfessionalProfile)
class ProfessionalProfile(SchemaConfigured, Persistent):
	createDirectFieldProperties(IProfessionalProfile)
	
	positions =  FP(IProfessionalProfile['positions'])

@WithRepr
@interface.implementer(IInterestProfile)
class InterestProfile(SchemaConfigured, Persistent):
	createDirectFieldProperties(IInterestProfile)
	
	interests =  FP(IInterestProfile['interests'])

@component.adapter(IUser)
@interface.implementer(ICompleteUserProfile)
class CompleteUserProfile(RestrictedUserProfile, # order matters
						  SocialMediaProfile,
						  InterestProfile,
						  EducationProfile,
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
				field = _ExistingDictReadFieldPropertyStoredThroughField(iface[_x],
																		 exist_name=field_map[_x])
			else:
				field = FP(iface[_x])

			setattr(clazz, _x, field)

	return clazz

def _init():
	# Map "existing"/legacy User/Entity dict storage to their new profile field
	_field_map = { 'alias': '_alias',
				   'realname': '_realname'}

	_class_map = {  
			IUserProfile: UserProfile,
			IFriendlyNamed: FriendlyNamed,
			ICompleteUserProfile: CompleteUserProfile,
			IRestrictedUserProfile: RestrictedUserProfile,
			IEmailRequiredUserProfile: EmailRequiredUserProfile,
			IRestrictedUserProfileWithContactEmail: RestrictedUserProfileWithContactEmail }

	for iface, clazz in _class_map.items():
		add_profile_fields(iface, clazz, field_map=_field_map)

_init()
del _init

FriendlyNamedFactory = afactory(FriendlyNamed)

RestrictedUserProfileFactory = afactory(RestrictedUserProfile)
RestrictedUserProfileWithContactEmailFactory = afactory(RestrictedUserProfileWithContactEmail)

COMPLETE_USER_PROFILE_KEY = 'nti.dataserver.users.user_profile.CompleteUserProfile'
CompleteUserProfileFactory = afactory(CompleteUserProfile,
									  key=COMPLETE_USER_PROFILE_KEY)

EMAIL_REQUIRED_USER_PROFILE_KEY = 'nti.dataserver.users.user_profile.EmailRequiredUserProfile'
EmailRequiredUserProfileFactory = afactory(EmailRequiredUserProfile,
										   key=EMAIL_REQUIRED_USER_PROFILE_KEY)
