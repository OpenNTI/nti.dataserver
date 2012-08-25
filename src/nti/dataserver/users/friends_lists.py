#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__( 'logging' ).getLogger( __name__ )

import six
import collections

from zope import interface
from zope import component
from zope.component.factory import Factory

import persistent

from nti.externalization.persistence import PersistentExternalizableList

from nti.ntiids import ntiids
from nti.utils import sets

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import enclosures
from nti.dataserver import mimetype

from .entity import Entity

def _get_shared_dataserver(context=None,default=None):
	if default != None:
		return component.queryUtility( nti_interfaces.IDataserver, context=context, default=default )
	return component.getUtility( nti_interfaces.IDataserver, context=context )



@interface.implementer(nti_interfaces.IFriendsList,nti_interfaces.ISimpleEnclosureContainer)
class FriendsList(enclosures.SimpleEnclosureMixin,Entity): #Mixin order matters for __setstate__
	""" A FriendsList or Circle belongs to a user and
	contains references (strings or weakrefs to principals) to other
	users. It has a name and ID, possibly a custom image.

	All mutations to the list must go through the APIs of this class. """

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	defaultGravatarType = 'wavatar'
	__external_can_create__ = True

	# FIXME: We really shouldn't depend on entity.
	# The only reason we're allowing - here right now is to work with existing tests.
	ALLOWED_USERNAME_CHARS = Entity.ALLOWED_USERNAME_CHARS + '-'

	def __init__(self, username=None, avatarURL=None):
		super(FriendsList,self).__init__(username, avatarURL)
		self._friends = None

	def _on_added_friend( self, friend ):
		if callable( getattr( friend, 'accept_shared_data_from', None ) ):
			friend.accept_shared_data_from( self.creator )
			self.creator.follow( friend ) # TODO: used to be an instance check on SharingSource

	def __iter__(self):
		"""
		Iterating over a FriendsList iterates over its friends
		(as Entity objects), resolving weak refs and strings.
		:return: An iterator across a set of `Entity` objects.
		"""
		# This function replaces things in the friends list as we
		# iterate across it, so we must iterate by index
		def _resolve_friend( friend, ix ):
			result = friend
			if isinstance( friend, six.string_types ):
				result = Entity.get_entity( friend, default=self )
				if result is self: result = None
				if result is not None:
					self._on_added_friend( result )
					# Now that we found it, if possible replace the string
					# with the real thing
					try:
						# Must have the index, the weak refs in here
						# behave badly in comparisons.
						self._friends[ix] = persistent.wref.WeakRef( result )
					except ValueError: pass
			elif isinstance( friend, persistent.wref.WeakRef ):
				result = friend()
			return result

		resolved = [_resolve_friend(self.friends[i], i) for i in xrange(len(self.friends))]
		return iter( {x for x in resolved if x is not None} )


	@property
	def friends(self):
		""" A sequence of strings, weak refs to Principals,
		arbitrary objects.

		Avoid this method. Prefer to iterate across this object."""
		return self._friends if self._friends is not None else []

	def addFriend( self, friend ):
		""" Adding friends causes our creator to follow them. """
		if friend is None: return
		# TODO: Why is this a list?
		if self._friends is None: self._friends = PersistentExternalizableList()
		if isinstance( friend, FriendsList ):
			# Recurse to generate the correct notifications
			for other_friend in friend.friends:
				self.addFriend( other_friend )
		elif isinstance( friend, Entity ):
			self._friends.append( persistent.wref.WeakRef( friend ) )
		elif isinstance( friend, collections.Mapping ) and 'Username' in friend:
			# Dictionaries and Dictionary-like things come in from
			# external representations. Resolve, then append.
			self.addFriend( Entity.get_entity( friend['Username'], default=friend['Username'] ) )
		elif isinstance( friend, six.string_types ):
			# Try to resolve, add the resolved if possible, otherwise add the
			# string as a placeholder. Don't recurse, could be infinite
			friend = friend.lower()
			friend = Entity.get_entity( friend, default=friend )
			self._friends.append( friend )
		else:
			self._friends.append( friend )

		self._on_added_friend( friend )

	@property
	def NTIID(self):
		return ntiids.make_ntiid( date=ntiids.DATE,
								  provider=self.creator.username if self.creator else 'Unknown',
								  nttype=ntiids.TYPE_MEETINGROOM_GROUP,
								  specific=self.username.lower().replace( ' ', '_' ).replace( '-', '_' ) )

	def get_containerId( self ):
		return 'FriendsLists'
	def set_containerId( self, cid ):
		pass
	containerId = property( get_containerId, set_containerId )


	def _update_friends_from_external(self, newFriends):

		self._friends = None
		for newFriend in newFriends:
			if isinstance( newFriend, basestring ) and callable( getattr( self.creator, 'getFriendsList', None ) ):
				otherList = self.creator.getFriendsList( newFriend )
				if otherList: newFriend = otherList
			self.addFriend( newFriend )

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(FriendsList,self).updateFromExternalObject( parsed, *args, **kwargs )
		updated = None
		newFriends = parsed.pop('friends', None)
		# Update, as usual, starts from scratch.
		# Notice we allow not sending friends to easily change
		# the realname, alias, etc
		if newFriends is not None:
			updated = True
			self._update_friends_from_external( newFriends )

		if self.username is None:
			self.username = parsed.get( 'Username' )
		if self.username is None:
			self.username = parsed.get( 'ID' )
		return updated

	@classmethod
	def _resolve_friends( cls, dataserver, parsed, externalFriends ):
		result = []
		for externalFriend in externalFriends:
			result.append( cls.get_entity( externalFriend, dataserver=dataserver, default=externalFriend ) )
		return result

	__external_resolvers__ = {'friends': _resolve_friends }


	def __eq__(self,other):
		result = super(FriendsList,self).__eq__(other)
		if result is True:
			try:
				result = self.friends == other.friends
			except AttributeError:
				result = NotImplemented
		return result
	def __lt__(self,other):
		result = super(FriendsList,self).__lt__(other)
		if result is True:
			result = self.friends < other.friends
		return result

@interface.implementer(nti_interfaces.IUsernameIterable)
@component.adapter(nti_interfaces.IFriendsList)
class _FriendsListUsernameIterable(object):

	def __init__( self, context ):
		self.context = context

	def __iter__(self):
		return (x.username for x in self.context)

from nti.dataserver.sharing import DynamicSharingTargetMixin


class DynamicFriendsList(DynamicSharingTargetMixin,FriendsList):
	"""
	An incredible hack to introduce a dynamic, but iterable
	user managed group/list.

	These are half FriendsList and half Community. When people are added
	to the list (and they don't get a veto), they are also added to the "community"
	that is this object. Their private _community set gets our NTIID
	added to it. The NTIID is resolvable through Entity.get_entity like magic,
	so this object will magically start appearing for them, and also will be
	searchable by them.
	"""
	__external_class_name__ = 'FriendsList'
	__external_can_create__ = False
	defaultGravatarType = 'retro'
	# Doesn't work because it's not in the instance dict, and the IModeledContent
	# interface value takes precedence over the class attribute
	mime_type = 'application/vnd.nextthought.friendslist'


	def _on_added_friend( self, friend ):
		assert self.creator, "Must have creator"
		super(DynamicFriendsList,self)._on_added_friend( friend )
		friend._communities.add( self.NTIID )
		friend._following.add( self.NTIID )
		# TODO: When this object is deleted we need to clean this up

	def _update_friends_from_external( self, new_friends ):
		old_friends = set( self )
		super(DynamicFriendsList,self)._update_friends_from_external( new_friends )
		new_friends = set( self )

		# New additions would have been added, we only have to take care of
		# removals.
		ex_friends = old_friends - new_friends
		for i_hate_you in ex_friends:
			sets.discard( i_hate_you._communities, self.NTIID )
			sets.discard( i_hate_you._following, self.NTIID )

	def accept_shared_data_from( self, source ):
		"""
		Override to save space. Only the membership matters.
		"""
		return True

	def ignore_shared_data_from( self, source ):
		"""
		Override to save space. Only the membership matters.
		"""
		return False

	def is_accepting_shared_data_from( self, source ):
		return source is self.creator or source in list(self)

from nti.dataserver import datastructures

@interface.implementer(nti_interfaces.IFriendsListContainer)
class _FriendsListMap(datastructures.AbstractCaseInsensitiveNamedLastModifiedBTreeContainer):


	contained_type = nti_interfaces.IFriendsList
	container_name = 'FriendsLists'


nti_interfaces.IFriendsList.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
											Factory( lambda extDict:  FriendsList( extDict['Username'] if 'Username' in extDict else extDict['ID'] ),
													 interfaces=(nti_interfaces.IFriendsList,)) )
