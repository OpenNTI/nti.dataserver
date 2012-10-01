#!/usr/bin/env python

import logging
logger = logging.getLogger( __name__ )

import random

from zope import component
from zope import interface

from nti.zodb import urlproperty

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import authorization_acl as auth

from nti.externalization.interfaces import IExternalObject
from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import to_standard_external_dictionary
from nti.externalization.oids import to_external_ntiid_oid

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
			link = links.Link( target=to_external_ntiid_oid(the_file), target_mime_type=the_file.mimeType, elements=('@@view',), rel="data" )
			interface.alsoProvides( link, nti_interfaces.ILinkExternalHrefOnly )
			return link
	return with_url.avatarURL

@component.adapter( nti_interfaces.IEntity )
@interface.implementer( IExternalObject )
class _EntitySummaryExternalObject(object):

	def __init__( self, entity ):
		self.entity = entity

	def toExternalObject( self ):
		"""
		Inspects the context entity and produces its external summary form.
		:return: Standard dictionary minus Last Modified plus the properties of this class.
			These properties include 'Username', 'avatarURL', 'realname', and 'alias'.

		"""
		entity = self.entity
		extDict = to_standard_external_dictionary( entity )
		# Notice that we delete the last modified date. Because this is
		# not a real representation of the object, we don't want people to cache based
		# on it.
		extDict.pop( 'Last Modified', None )
		extDict['Username'] = entity.username
		extDict['avatarURL'] = _avatar_url( entity )
		names = interfaces.IFriendlyNamed( entity )
		extDict['realname'] = names.realname or entity.username
		extDict['alias'] = names.alias or names.realname or entity.username
		extDict['CreatedTime'] = getattr( self, 'createdTime', 42 ) # for migration
		extDict.__parent__ = entity.__parent__
		extDict.__name__ = entity.__name__
		extDict.__acl__ = auth.ACL( entity )
		return extDict


class _EntityExternalObject(_EntitySummaryExternalObject):

	def toExternalObject( self ):
		""" :return: The value of :meth:`toSummaryExternalObject` """
		result = super(_EntityExternalObject,self).toExternalObject()
		# restore last modified since we are the true representation
		result['Last Modified'] = getattr( self.entity, 'lastModified', 0 )
		return result


@component.adapter( nti_interfaces.IFriendsList )
class _FriendsListExternalObject(_EntityExternalObject):

	def toExternalObject(self):
		extDict = super(_FriendsListExternalObject,self).toExternalObject()
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

@component.adapter( nti_interfaces.IUser )
class _UserSummaryExternalObject(_EntitySummaryExternalObject):

	def toExternalObject( self ):
		extDict = super(_UserSummaryExternalObject,self).toExternalObject( )

		# TODO: Is this a privacy concern?
		extDict['lastLoginTime'] = self.entity.lastLoginTime.value
		extDict['NotificationCount'] = self.entity.notificationCount.value
		prof = interfaces.IUserProfile( self.entity )
		extDict['affiliation'] = getattr( prof, 'affiliation', None )
		return extDict

@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class _CoppaUserSummaryExternalObject(_UserSummaryExternalObject):

	def toExternalObject( self ):
		extDict = super(_CoppaUserSummaryExternalObject,self).toExternalObject( )
		extDict['affiliation'] = None
		return extDict


@component.adapter( nti_interfaces.IUser )
class _UserPersonalSummaryExternalObject(_UserSummaryExternalObject):

	def toExternalObject( self ):
		"""
		:return: the externalization intended to be sent when requested by this user.
		"""
		from nti.dataserver._Dataserver import InappropriateSiteError # circular imports
		extDict = super(_UserPersonalSummaryExternalObject,self).toExternalObject()
		def ext( l, name='summary' ):
			result = []
			for ent_name in l:
				__traceback_info__ = name, ent_name
				try:
					e = self.entity.get_entity( ent_name, default=self )
					e = None if e is self else e # Defend against no dataserver component to resolve with
				except InappropriateSiteError:
					# We've seen this in logging that is captured and happens
					# after things finish running, notably nose's logcapture.
					e = None

				if e:
					result.append( toExternalObject( e, name=name ) )
				# It screws up the web app if we return strings here for things that do not yet or
				# do not anymore exist. Even though we've always done that.

			return result

		prof = interfaces.IRestrictedUserProfile( self.entity )
		extDict['email'] = prof.email
		extDict['birthdate'] = prof.birthdate.isoformat() if prof.birthdate is not None else None

		# Communities are not currently editable,
		# and will need special handling of Everyone
		extDict['Communities'] = ext(self.entity.communities, name='')
		# Following is writable
		extDict['following'] = ext(self.entity.following)
		# as is ignoring and accepting
		extDict['ignoring'] = ext(self.entity.ignoring_shared_data_from)
		extDict['accepting'] = ext(self.entity.accepting_shared_data_from)
		extDict['AvatarURLChoices'] = component.getAdapter( self.entity, interfaces.IAvatarChoices ).get_choices()
		extDict['Links'] = self._replace_or_add_edit_link_with_self( extDict.get( 'Links', () ) )
		extDict['Last Modified'] = getattr( self.entity, 'lastModified', 0 )

		most_derived_profile_iface = _ext_find_schema( prof, interfaces.IRestrictedUserProfile )
		for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
			if name in extDict or field.queryTaggedValue( interfaces.TAG_HIDDEN_IN_UI ) or interface.interfaces.IMethod.providedBy( field ):
				continue
			extDict[name] = field.query( prof )

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

_UserExternalObject = _UserPersonalSummaryExternalObject

@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class _CoppaUserPersonalSummaryExternalObject(_UserPersonalSummaryExternalObject):

	def toExternalObject( self ):
		extDict = super(_CoppaUserPersonalSummaryExternalObject,self).toExternalObject( )
		for k in ('affiliation', 'email', 'birthdate', 'contact_email'):
			extDict[k] = None
		return extDict

_CoppaUserExternalObject = _CoppaUserPersonalSummaryExternalObject

from nti.utils.schema import find_most_derived_interface as _ext_find_schema
