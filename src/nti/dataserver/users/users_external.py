#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations for user externalization.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import random
import functools

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import authorization_acl as auth

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.interfaces import IExternalObject
from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import to_standard_external_dictionary, decorate_external_mapping

from nti.schema.interfaces import find_most_derived_interface

from nti.zodb import urlproperty

from . import interfaces

def _avatar_url( entity ):
	"""
	Takes into account file storage and generates Link objects
	instead of data: urls. Tightly coupled to user_profile.
	"""

	with_url = interfaces.IAvatarURL( entity )
	url_property = getattr( type(with_url), 'avatarURL', None )
	if isinstance( url_property, urlproperty.UrlProperty ):
		the_file = url_property.get_file( with_url )
		if the_file:
			# TODO: View name. Coupled to the app layer
			# It's not quite possible to fully traverse to the file if the profile
			# is implemented as an annotation (and that exposes lots of internal details)
			# so we go directly to the file address
			target = to_external_ntiid_oid( the_file, add_to_connection=True )
			if target:
				link = links.Link( target=target, target_mime_type=the_file.mimeType, elements=('@@avatar_view',), rel="data" )
				interface.alsoProvides( link, nti_interfaces.ILinkExternalHrefOnly )
				return link
			logger.warn( "Unable to produce avatarURL for %s", entity )
	return with_url.avatarURL


@interface.implementer( IExternalObject )
class _AbstractEntitySummaryExternalObject(object):

	def __init__( self, entity ):
		self.entity = entity

	_DECORATE = False
	def _do_toExternalObject( self, **kwargs ):
		"""
		Inspects the context entity and produces its external summary form.
		:return: Standard dictionary minus Last Modified plus the properties of this class.
			These properties include 'Username', 'avatarURL', 'realname', and 'alias'.

		"""
		entity = self.entity
		extDict = to_standard_external_dictionary( entity, decorate=False, **kwargs )
		# Notice that we delete the last modified date. Because this is
		# not a real representation of the object, we don't want people to cache based
		# on it.
		extDict.pop( 'Last Modified', None )
		extDict['Username'] = entity.username
		extDict['avatarURL'] = _avatar_url( entity )
		names = interfaces.IFriendlyNamed( entity )
		extDict['realname'] = names.realname or entity.username
		extDict['alias'] = names.alias or names.realname or entity.username
		extDict['CreatedTime'] = getattr( entity, 'createdTime', 42 ) # for migration
		extDict.__parent__ = entity.__parent__
		extDict.__name__ = entity.__name__
		# we'd like to make the ACL available. Pyramid
		# supports either a callable or the flattened list;
		# defer it until/if we need it by using a callable because
		# computing it can be expensive if the cache is cold.
		extDict.__acl__ = functools.partial( auth.ACL, entity )
		return extDict

	def toExternalObject( self, **kwargs ):
		# Break this into two steps to ensure that we only try to
		# decorate the external mapping when all the objects in the hierarchy
		# have completed their work and the mapping is complete
		extDict = self._do_toExternalObject( **kwargs )
		if self._DECORATE:
			decorate_external_mapping( self.entity, extDict )
		return extDict

@component.adapter( nti_interfaces.IEntity )
class _EntitySummaryExternalObject(_AbstractEntitySummaryExternalObject):
	_DECORATE = True

@component.adapter( nti_interfaces.IFriendsList )
class _FriendListSummaryExternalObject(_AbstractEntitySummaryExternalObject):
	_DECORATE = True
	def _do_toExternalObject( self, **kwargs ):
		extDict = super(_FriendListSummaryExternalObject, self)._do_toExternalObject(**kwargs)
		extDict['IsDynamicSharing'] = nti_interfaces.IDynamicSharingTarget.providedBy( self.entity )
		return extDict

@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
class _DynamicFriendListSummaryExternalObject(_FriendListSummaryExternalObject):

	def _do_toExternalObject(self, **kwargs):
		extDict = super(_DynamicFriendListSummaryExternalObject, self)._do_toExternalObject(**kwargs)
		extDict['Locked'] = self.entity.Locked
		return extDict

class _EntityExternalObject(_EntitySummaryExternalObject):

	def _do_toExternalObject( self, **kwargs ):
		""" :return: The value of :meth:`toSummaryExternalObject` """
		result = super(_EntityExternalObject,self)._do_toExternalObject(**kwargs)
		# restore last modified since we are the true representation
		result['Last Modified'] = getattr( self.entity, 'lastModified', 0 )
		return result

@component.adapter( nti_interfaces.IFriendsList )
class _FriendsListExternalObject(_EntityExternalObject):

	def _do_toExternalObject(self, **kwargs):
		extDict = super(_FriendsListExternalObject,self)._do_toExternalObject(**kwargs)
		theFriends = []
		for friend in iter(self.entity): #iter self to weak refs and dups
			if isinstance( friend, users.Entity ):
				# NOTE: We've got a potential infinite recursion here. Normally
				# users cannot be their own friends. But a DFL might make it
				# appear that way. The DFL would show up in the communities of the
				# personal-summary too, which would get us back here. So we
				# must not use personal-summary here.
				if friend == self.entity.creator:
					friend = toExternalObject( friend, name='summary' )
				else:
					friend = toExternalObject( friend, name='summary' )
				theFriends.append( friend )

		extDict['friends'] = theFriends
		extDict['CompositeGravatars'] = self._composite_gravatars()
		# We took great care to make DFLs and FLs indistinguishable from each other
		# in the external form, to make things easier for the UI. This now
		# comes back to bite us when we need to make that distinction.
		extDict['IsDynamicSharing'] = nti_interfaces.IDynamicSharingTarget.providedBy( self.entity )

		return extDict

	def _composite_gravatars(self):
		""""
		:return: A consistent list of gravatars for the users in this list. The idea is to
			shuffle them such that they are recognizable, even among different lists
			with similar memberships (that's why sorting wouldn't work).
		"""
		# We do this simply by selecting 4 random users, seeded based on the name of this
		# object.
		# TODO: Is there a better seed?
		friends = [_avatar_url(x) for x in self.entity]
		if not friends:
			return ()
		rand = random.Random( hash(self.entity.username) )
		return rand.sample( friends, min(4,len(friends)) )

@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
class _DynamicFriendsListExternalObject(_FriendsListExternalObject):

	def _do_toExternalObject(self, **kwargs):
		extDict = super(_DynamicFriendsListExternalObject, self)._do_toExternalObject(**kwargs)
		extDict['Locked'] = self.entity.Locked
		return extDict

@component.adapter( nti_interfaces.IUser )
class _UserSummaryExternalObject(_EntitySummaryExternalObject):

	#: Even in summary (i.e. to other people), we want to publish all these fields
	#: because it looks better
	public_summary_profile_fields = ('affiliation', 'home_page', 'description', 'location', 'role', 'about')
	# These could probably be put as tags on the interface fields, but the number of
	# profile interfaces in use makes that a chore. At the moment, this is the simpler option

	def _do_toExternalObject( self, **kwargs ):
		extDict = super(_UserSummaryExternalObject,self)._do_toExternalObject( **kwargs )

		extDict['lastLoginTime'] = self.entity.lastLoginTime
		if self.public_summary_profile_fields:
			prof = interfaces.IUserProfile( self.entity )
			for f in self.public_summary_profile_fields:
				extDict[f] = getattr( prof, f, None )
		return extDict

@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class _CoppaUserSummaryExternalObject(_UserSummaryExternalObject):
	#: Privacy is very important for the precious children. None of their profile
	#: fields are public to other people.
	public_summary_profile_fields = ()


@component.adapter( nti_interfaces.IUser )
class _UserPersonalSummaryExternalObject(_UserSummaryExternalObject):

	def _do_toExternalObject( self, **kwargs ):
		"""
		:return: the externalization intended to be sent when requested by this user.
		"""
		from nti.dataserver._Dataserver import InappropriateSiteError # circular imports
		extDict = super(_UserPersonalSummaryExternalObject,self)._do_toExternalObject(**kwargs)
		def _externalize_subordinates( l, name='summary' ):
			result = []
			for ent_name in l:
				__traceback_info__ = name, ent_name
				if nti_interfaces.IEntity.providedBy( ent_name ):
					e = ent_name
				else:
					try:
						e = self.entity.get_entity( ent_name, default=self )
						e = None if e is self else e # Defend against no dataserver component to resolve with
					except InappropriateSiteError:
						# We've seen this in logging that is captured and happens
						# after things finish running, notably nose's logcapture.
						e = None

				if e:
					try:
						kw = kwargs
						if 'name' in kw:
							kw = kwargs.copy()
							kw.pop('name')
						result.append( toExternalObject( e, name=name, **kw ) )
					except TypeError: # Thrown if we fail in certain parts of externalization (e.g., links)
						# TODO: Better exception?
						# TODO: It may not be good to do this, that may hide errors that need to be corrected
						logger.exception( "Failed to externalize subordinate object %r of %r", e, self.entity )

				# It screws up the web app if we return strings here for things that do not yet or
				# do not anymore exist. Even though we've always done that.

			return result

		extDict['NotificationCount'] = self.entity.notificationCount.value

		prof = interfaces.IRestrictedUserProfile( self.entity )
		extDict['email'] = prof.email
		extDict['birthdate'] = prof.birthdate.isoformat() if prof.birthdate is not None else None

		# DynamicMemberships/Communities are not currently editable,
		# and will need special handling of (a) Everyone and (b) DynamicFriendsLists
		# (proper events could handle the latter)
		extDict['Communities'] = _externalize_subordinates(
									self.entity.xxx_hack_filter_non_memberships( self.entity.dynamic_memberships,
																				 log_msg="Relationship trouble. User %s is no longer a member of %s. Ignoring for externalization",
																				 the_logger=logger),
									name='') # Deprecated
		extDict['DynamicMemberships'] = extDict['Communities']

		# Following is writable
		extDict['following'] = _externalize_subordinates( self.entity.xxx_hack_filter_non_memberships( self.entity.entities_followed ) )
		# as is ignoring and accepting
		extDict['ignoring'] = _externalize_subordinates(self.entity.entities_ignoring_shared_data_from)
		extDict['accepting'] = _externalize_subordinates(self.entity.entities_accepting_shared_data_from)
		extDict['AvatarURLChoices'] = component.getAdapter( self.entity, interfaces.IAvatarChoices ).get_choices()
		extDict['Links'] = self._replace_or_add_edit_link_with_self( extDict.get( 'Links', () ) )
		extDict['Last Modified'] = getattr( self.entity, 'lastModified', 0 )

		# Ok, we did the standard profile fields. Now, find the most derived interface
		# for this profile and write the additional fields
		most_derived_profile_iface = find_most_derived_interface( prof, interfaces.IRestrictedUserProfile )
		for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
			if name in extDict or field.queryTaggedValue( interfaces.TAG_HIDDEN_IN_UI ) or interface.interfaces.IMethod.providedBy( field ):
				continue
			# Save the value from the profile, or if the profile doesn't have it yet,
			# use the default (if there is one). Otherwise its None
			extDict[name] = field.query( prof, getattr( field, 'default', None ) )

		return extDict

	def _replace_or_add_edit_link_with_self( self, _links ):
		added = False
		_links = list( _links )
		for i, l in enumerate(_links):
			if l.rel == 'edit':
				_links[i] = links.Link( self.entity, rel='edit' )
				added = True
		if not added:
			_links.append( links.Link( self.entity, rel='edit' ) )

		return _links

# By default, when externalizing we send the minimum public data.
# A few places exist, such as the resolve user api, that can
# get the 'complete' data by asking for the registered 'personal'
# externalizer
from pyramid.threadlocal import get_current_request

def _named_externalizer(user):
	# XXX This doesn't exactly belong at this layer. Come up with
	# a better way to do this switching.
	req = get_current_request()
	if req is None or req.authenticated_userid is None or req.authenticated_userid != user.username:
		return 'summary'
	return 'personal-summary'

@interface.implementer( IExternalObject )
@component.adapter( nti_interfaces.IUser )
def _UserExternalObject(user):
	return component.getAdapter(user,IExternalObject,name=_named_externalizer(user))

@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class _CoppaUserPersonalSummaryExternalObject(_UserPersonalSummaryExternalObject):

	def _do_toExternalObject( self, **kwargs ):
		extDict = super(_CoppaUserPersonalSummaryExternalObject,self)._do_toExternalObject( **kwargs )
		for k in ('affiliation', 'email', 'birthdate', 'contact_email', 'location', 'home_page'):
			extDict[k] = None
		return extDict

@interface.implementer( IExternalObject )
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
def _CoppaUserExternalObject(user):
	return component.getAdapter(user,IExternalObject,name=_named_externalizer(user))
