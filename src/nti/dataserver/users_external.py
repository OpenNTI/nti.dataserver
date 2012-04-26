#!/usr/bin/env python

import logging
logger = logging.getLogger( __name__ )

import random

from zope import component
from zope import interface

from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import links

from nti.externalization.interfaces import IExternalObject
from nti.externalization.externalization import toExternalObject
from nti.externalization.oids import to_external_ntiid_oid


class _EntitySummaryExternalObject(object):
	component.adapts( nti_interfaces.IEntity )
	interface.implements( IExternalObject )

	def __init__( self, entity ):
		self.entity = entity


	def toExternalObject( self ):
		"""
		:return: Standard dictionary minus Last Modified plus the properties of this class.
			These properties include 'Username', 'avatarURL', 'realname', and 'alias'.

		EOD
		"""
		entity = self.entity
		extDict = entity.toExternalDictionary( )
		# Notice that we delete the last modified date. Because this is
		# not a real representation of the object, we don't want people to cache based
		# on it.
		extDict.pop( 'Last Modified', None )
		extDict['Username'] = entity.username
		extDict['avatarURL'] = entity.avatarURL
		extDict['realname'] = entity.realname
		extDict['alias'] = entity.alias
		extDict['CreatedTime'] = getattr( self, 'createdTime', 42 ) # for migration
		return extDict


class _EntityExternalObject(_EntitySummaryExternalObject):

	def toExternalObject( self ):
		""" :return: The value of :meth:`toSummaryExternalObject` """
		result = super(_EntityExternalObject,self).toExternalObject()
		# restore last modified since we are the true representation
		result['Last Modified'] = getattr( self, 'lastModified', 0 )
		return result



class _FriendsListExternalObject(_EntityExternalObject):

	component.adapts( nti_interfaces.IFriendsList )


	def toExternalObject(self):
		extDict = super(_FriendsListExternalObject,self).toExternalObject()
		theFriends = []
		for friend in iter(self.entity): #iter self to weak refs and dups
			if isinstance( friend, users.Entity ):
				if friend == self.entity.creator:
					friend = toExternalObject( friend, name='personal-summary' )
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
		friends = [x.avatarURL for x in self.entity]
		if not friends:
			return ()
		rand = random.Random( hash(self.entity.username) )
		return rand.sample( friends, min(4,len(friends)) )

class _UserSummaryExternalObject(_EntitySummaryExternalObject):
	component.adapts( nti_interfaces.IUser )

	def toExternalObject( self ):
		extDict = super(_UserSummaryExternalObject,self).toExternalObject( )

		# TODO: Is this a privacy concern?
		extDict['lastLoginTime'] = self.entity.lastLoginTime.value
		extDict['NotificationCount'] = self.entity.notificationCount.value
		return extDict


class _UserPersonalSummaryExternalObject(_UserSummaryExternalObject):
	component.adapts( nti_interfaces.IUser )


	def toExternalObject( self ):
		"""
		:return: the externalization intended to be sent when requested by this user.
		"""

		from nti.dataserver._Dataserver import InappropriateSiteError # circular imports
		extDict = super(_UserPersonalSummaryExternalObject,self).toExternalObject()
		def ext( l ):
			result = []
			for name in l:
				try:
					e = self.entity.get_entity( name, default=self )
					e = None if e is self else e # Defend against no dataserver component to resolve with
				except InappropriateSiteError:
					# We've seen this in logging that is captured and happens
					# after things finish running, notably nose's logcapture.
					e = None

				result.append( toExternalObject( e, name='summary' ) if e else name )

			return result

		# Communities are not currently editable,
		# and will need special handling of Everyone
		extDict['Communities'] = ext(self.entity.communities)
		# Following is writable
		extDict['following'] = ext(self.entity.following)
		# as is ignoring and accepting
		extDict['ignoring'] = ext(self.entity.ignoring_shared_data_from)
		extDict['accepting'] = ext(self.entity.accepting_shared_data_from)
		extDict['Links'] = [ links.Link( to_external_ntiid_oid( self.entity ), rel='edit' ) ]
		extDict['Last Modified'] = getattr( self.entity, 'lastModified', 0 )
		return extDict

_UserExternalObject = _UserPersonalSummaryExternalObject
