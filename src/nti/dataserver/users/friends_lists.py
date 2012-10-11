#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__( 'logging' ).getLogger( __name__ )

from zope import interface
from zope import component
from zope.component.factory import Factory

from BTrees.OOBTree import OOTreeSet, difference as OOBTree_difference

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


	def __init__(self, username=None, avatarURL=None):
		super(FriendsList,self).__init__(username, avatarURL)
		# We store our friends in a sorted set of weak references
		# It's unlikely to have many empty friendslist objects, so it makes sense
		# to create it now
		self._friends_wref_set = OOTreeSet()


	def _on_added_friend( self, friend ):
		"""
		Called with an Entity object when a new friend is added
		"""
		if callable( getattr( friend, 'accept_shared_data_from', None ) ):
			friend.accept_shared_data_from( self.creator )
			self.creator.follow( friend ) # TODO: used to be an instance check on SharingSource

	def __iter__(self):
		"""
		Iterating over a FriendsList iterates over its friends
		(as Entity objects), resolving weak refs.
		:return: An iterator across a set of `Entity` objects.
		"""
		return (x() for x in self._friends_wref_set if x())


	def addFriend( self, friend ):
		"""
		Adding friends causes our creator to follow them.

		:param friend: Perhaps unwisely, we will accept a few potential values
			for `friend`. In the simplest most desired case, it may be an existing, named Entity.
			It may not be this list or this list's creator.

		:return: A count of the number of friends added to this list, usually
			0 or 1. May be treated as a boolean to determine if the object was actually added
			or was either already a member of this list or of an unrecognized type.

		"""
		if friend is None or friend is self or friend is self.creator:
			return 0

		if not isinstance( friend, Entity ):
			try:
				friend = self.get_entity( friend, default=friend )
			except TypeError:
				pass

		result = False
		if isinstance( friend, Entity ):
			wref = nti_interfaces.IWeakRef( friend )
			assert wref.username == friend.username
			result = self._friends_wref_set.add( wref )
			if result:
				self._on_added_friend( friend )

		return result

	@property
	def NTIID(self):
		# TODO: Cache this. @CachedProperty?
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
		new_entities = []

		for newFriend in newFriends:
			# For the sake of unit tests, we need to do resolution here. but only of string
			# names
			if not isinstance( newFriend, Entity ):
				try:
					newFriend = self.get_entity( newFriend, default=newFriend )
				except TypeError:
					pass

			if isinstance( newFriend, Entity ) and newFriend != self.creator:
				new_entities.append( newFriend )

		result = 0
		incoming_entities = OOTreeSet( new_entities )
		current_entities = OOTreeSet()
		broken_refs = []
		for x in self._friends_wref_set:
			ent = x(allow_cached=False)
			if ent is not None:
				current_entities.add( ent )
			else:
				broken_refs.append( x )

		for x in broken_refs:
			result += 1
			self._friends_wref_set.remove( x )

		# What's incoming that I don't have
		missing_entities = OOBTree_difference( incoming_entities, current_entities )

		# What I do have that I should no longer have
		extra_entities = OOBTree_difference( current_entities, incoming_entities )

		# Now sync
		for x in missing_entities:
			result += self.addFriend( x )

		for x in extra_entities:
			self._friends_wref_set.remove( nti_interfaces.IWeakRef( x ) )
			result += 1

		if __debug__:
			__traceback_info__ = list(sorted(incoming_entities)), list(sorted(self))
			assert list(sorted(incoming_entities)) == list(sorted(self))

		return result

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(FriendsList,self).updateFromExternalObject( parsed, *args, **kwargs )
		updated = None
		newFriends = parsed.pop('friends', None)
		# Update, as usual, starts from scratch.
		# Notice we allow not sending friends to easily change
		# the realname, alias, etc
		if newFriends is not None:
			__traceback_info__ = newFriends
			update_count = self._update_friends_from_external( newFriends )
			updated = update_count > 0

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
				result = self.creator == other.creator and set(self) == set(other)
			except (AttributeError,TypeError):
				result = NotImplemented
		return result

	def __lt__(self,other):
		result = super(FriendsList,self).__lt__(other)
		if result is True:
			try:
				result = self.creator < other.creator and sorted(self) < sorted(other)
			except (AttributeError,TypeError):
				result = NotImplemented
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

	# TODO: Users can leave these things by editing their 'communities' attribute
	# When that happens, we need to catch that event and remove them from here
	# as well. Or somehow tie the things closer together.

	def _on_added_friend( self, friend ):
		assert self.creator, "Must have creator"
		super(DynamicFriendsList,self)._on_added_friend( friend )
		if hasattr( friend, '_communities' ) and hasattr( friend, '_following' ):
			# TODO: This is here to support the weird unresolved friend-as-string
			# thing
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

@interface.implementer(nti_interfaces.IUsernameIterable)
@component.adapter(DynamicFriendsList)
class _DynamicFriendsListUsernameIterable(_FriendsListUsernameIterable):
	"""
	Iterates the contained friends, but also includes the creator
	of the DFL. The primary reason to do this is that the only place
	this interface is used is with sharing, and this ensures
	that the creator gets notices.
	"""

	def __iter__( self ):
		names = {x.username for x in self.context}
		names.add( self.context.creator.username )
		return iter(names)

from nti.dataserver import datastructures

@interface.implementer(nti_interfaces.IFriendsListContainer)
class _FriendsListMap(datastructures.AbstractCaseInsensitiveNamedLastModifiedBTreeContainer):


	contained_type = nti_interfaces.IFriendsList
	container_name = 'FriendsLists'


nti_interfaces.IFriendsList.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
											Factory( lambda extDict:  FriendsList( extDict['Username'] if 'Username' in extDict else extDict['ID'] ),
													 interfaces=(nti_interfaces.IFriendsList,)) )
