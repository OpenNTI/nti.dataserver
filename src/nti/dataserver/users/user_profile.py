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

from zope.schema.fieldproperty import FieldPropertyStoredThroughField

from nti.dataserver import interfaces as nti_interfaces
from . import interfaces

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

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IFriendlyNamed,zope.location.interfaces.ILocation)
class FriendlyNamed(persistent.Persistent):
	"""
	An adapter for storing naming data for users. Intended to be an annotation, used with
	an annotation factory; in this way we keep the context as our parent, but taket
	it as an optional argument for ease of testing.
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

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.IUserProfile)
class UserProfile(FriendlyNamed):
	"""
	An adapter for storing profile information. We provide a specific implementation
	of the ``avatarURL`` property rather than relying on field storage.
	"""

	avatarURL = property( lambda self: getattr( self, '_avatarURL', None ) or interfaces.IAvatarURLProvider(self.context).avatarURL,
						  lambda self, nv: setattr( self, '_avatarURL', nv ),
						  lambda self: delattr( self, '_avatarURL' ) )

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.IRestrictedUserProfile)
class RestrictedUserProfile(UserProfile):

	# If anyone tries to set an email on us, we turn it into the recovery hash
	email = property( lambda self: None,
					  lambda self, nv: setattr( self, 'password_recovery_email_hash', unicode(hashlib.sha1( nv ).hexdigest()) ),
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
		for _x in iface.names():
			# Since the names are defined and may be overrides,
			# we also let overrides happen in the class dicts
			if not _x in clazz.__dict__:
				setattr( clazz,
						 _x,
						 _ExistingDictReadFieldPropertyStoredThroughField(
							 iface[_x],
							 exist_name=_field_map.get( _x ) ) )
_init()
del _init

FriendlyNamedFactory = zope.annotation.factory( FriendlyNamed )
RestrictedUserProfileFactory = zope.annotation.factory( RestrictedUserProfile )
RestrictedUserProfileWithContactEmailFactory = zope.annotation.factory( RestrictedUserProfileWithContactEmail )
CompleteUserProfileFactory = zope.annotation.factory( CompleteUserProfile )
EmailRequiredUserProfileFactory = zope.annotation.factory( EmailRequiredUserProfile )
