#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of user profile related storage.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
import zope.location.interfaces
import zope.annotation

import persistent
import hashlib
import nameparser

from zope.schema.fieldproperty import FieldPropertyStoredThroughField

from nti.zodb import urlproperty
from nti.dataserver import interfaces as nti_interfaces
from . import interfaces

from nti.utils.property import CachedProperty

class _ExistingDictReadFieldPropertyStoredThroughField(FieldPropertyStoredThroughField):
	"""
	Migration from existing data fields in instance dictionaries to
	our profile storage. There are probably few enough of these in places we care
	about to be almost unnecessary.
	"""
	_existing_name = None
	def __init__( self, field, name=None, exist_name=None ):
		super(_ExistingDictReadFieldPropertyStoredThroughField,self).__init__( field, name=name )
		if exist_name:
			self._existing_name = exist_name

	def getValue( self, inst, field):
		ex_val = getattr( inst.context, self._existing_name or 'This Value Cannot Be an Attr', None )
		if ex_val:
			return ex_val
		return super(_ExistingDictReadFieldPropertyStoredThroughField,self).getValue( inst, field )

	def setValue( self, inst, field, value ):
		try:
			del inst.context.__dict__[self._existing_name]
		except KeyError:
			pass
		super(_ExistingDictReadFieldPropertyStoredThroughField,self).setValue( inst, field, value )
		# We're not implementing the queryValue method, which is used
		# somehow when the field is readonly and...something
		# We don't use this for readonly fields, so we don't care

####
## The profile classes use schema fields to define what can be stored
## and to perform validation. The schema fields are handled dynamically with the
## fieldproperty classes, and are added to the classes themselves dynamically in _init
####
# TODO: Isn't this extremely similar to dm.zope.schema? Did we forget about that?

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IFriendlyNamed,zope.location.interfaces.ILocation)
class FriendlyNamed(persistent.Persistent):
	"""
	An adapter for storing naming data for users. Intended to be an
	annotation, used with an annotation factory; in that scenario, the
	"context" of the annotation is actually the ``__parent__`` (as set
	by the factory). However, for ease of testing, we can also
	explicitly accept the context as an optional argument to the
	constructor.
	"""

	__parent__ = None
	__name__ = None

	def __init__( self, context=None ):
		super(FriendlyNamed,self).__init__()
		if context:
			self.__parent__ = context

	@property
	def context(self):
		return self.__parent__

	@CachedProperty('realname')
	def _searchable_realname_parts(self):
		# This implementation is quite naive, returning
		# first middle and last if they are not blank. How does
		# this handle more complex naming scenarios?
		if self.realname:
			# because we are cached, be sure to return an immutable
			# value
			return tuple([x for x in nameparser.HumanName(self.realname)[1:4] if x])
		# Returning none keeps the entity out of the index

	def get_searchable_realname_parts(self):
		return self._searchable_realname_parts


class _AvatarUrlProperty(urlproperty.UrlProperty):
	"""
	Adds a default value if nothing is set for the instance.

	Requires either a data: url or a complete URL, not a host-relative URL;
	host-relative URLs are ignored (as an attempt to update-in-place the same
	externalized URL).
	"""

	ignore_url_with_missing_host = True

	# TODO: Should we be scaling this now?
	# TODO: Should we be enforcing constraints on this? Like max size,
	# ensuring it really is an image, etc? With arbitrary image uploading, we risk
	# being used as a dumping ground for illegal/copyright infringing material
	def __get__( self, instance, owner ):
		result = super(_AvatarUrlProperty,self).__get__( instance, owner )
		if not result:
			result = interfaces.IAvatarURLProvider(instance.context).avatarURL
		return result

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.IUserProfile)
class UserProfile(FriendlyNamed):
	"""
	An adapter for storing profile information. We provide a specific implementation
	of the ``avatarURL`` property rather than relying on field storage.

	For convenience, we have a read-only shadow of the username value.
	"""
	### NOTE: See users_external, this is fairly tightly coupled to that
	_avatarURL = None
	avatarURL = _AvatarUrlProperty( data_name="avatarURL", url_attr_name='_avatarURL', file_attr_name='_avatarURL' )
	__getitem__ = avatarURL.make_getitem()

	username = property( lambda self: self.context.username )

def make_password_recovery_email_hash( email ):
	if not email:
		raise ValueError("Must provide email")
	email = email.lower() # ensure casing is consistent
	return unicode( hashlib.sha1( email ).hexdigest() )

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.IRestrictedUserProfile)
class RestrictedUserProfile(UserProfile):

	# If anyone tries to set an email on us, we turn it into the recovery hash
	email = property( lambda self: None,
					  lambda self, nv: setattr( self, 'password_recovery_email_hash', make_password_recovery_email_hash( nv ) ),
					  doc="This type of profile cannot store an actual email address. If anyone tries, it becomes the recovery hash")

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.IRestrictedUserProfileWithContactEmail)
class RestrictedUserProfileWithContactEmail(RestrictedUserProfile):
	pass

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.ICompleteUserProfile)
class CompleteUserProfile(RestrictedUserProfile):
	pass



@interface.implementer(interfaces.IEmailRequiredUserProfile)
class EmailRequiredUserProfile(CompleteUserProfile):
	"""
	An adapter for requiring the email.
	"""

def add_profile_fields( iface, clazz, field_map=None ):
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
				field = _ExistingDictReadFieldPropertyStoredThroughField( iface[_x], exist_name=field_map[_x] )
			else:
				field = FieldPropertyStoredThroughField( iface[_x] )

			setattr( clazz,
					 _x,
					 field )

	return clazz

def _init():

	# Map "existing"/legacy User/Entity dict storage to their new profile field
	_field_map = { 'alias': '_alias',
				   'realname': '_realname'}

	_class_map = { interfaces.IFriendlyNamed: FriendlyNamed,
				   interfaces.IUserProfile: UserProfile,
				   interfaces.IRestrictedUserProfile: RestrictedUserProfile,
				   interfaces.IRestrictedUserProfileWithContactEmail: RestrictedUserProfileWithContactEmail,
				   interfaces.ICompleteUserProfile: CompleteUserProfile,
				   interfaces.IEmailRequiredUserProfile: EmailRequiredUserProfile }

	for iface, clazz in _class_map.items():
		add_profile_fields( iface, clazz, field_map=_field_map )

_init()
del _init

FriendlyNamedFactory = zope.annotation.factory( FriendlyNamed )
RestrictedUserProfileFactory = zope.annotation.factory( RestrictedUserProfile )
RestrictedUserProfileWithContactEmailFactory = zope.annotation.factory( RestrictedUserProfileWithContactEmail )
COMPLETE_USER_PROFILE_KEY = 'nti.dataserver.users.user_profile.CompleteUserProfile'
CompleteUserProfileFactory = zope.annotation.factory( CompleteUserProfile, key=COMPLETE_USER_PROFILE_KEY )
EMAIL_REQUIRED_USER_PROFILE_KEY = 'nti.dataserver.users.user_profile.EmailRequiredUserProfile'
EmailRequiredUserProfileFactory = zope.annotation.factory( EmailRequiredUserProfile, key=EMAIL_REQUIRED_USER_PROFILE_KEY )
