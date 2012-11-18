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

from BTrees.OOBTree import OOTreeSet, difference as OOBTree_difference, intersection as OOBTree_intersection

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
class FriendsList(enclosures.SimpleEnclosureMixin,Entity): # Mixin order matters for __setstate__
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
			__traceback_info__ = friend, wref
			assert wref.username.lower() == friend.username.lower()
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
								  specific=ntiids.escape_provider(self.username.lower()))

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
		for x in self._friends_wref_set:
			ent = x(allow_cached=False)
			if ent is not None:
				current_entities.add( ent )
			else:
				# broken ref. So we are effectively mutating this entity
				result += 1


		# What's incoming that I don't have
		missing_entities = OOBTree_difference( incoming_entities, current_entities )

		# What's incoming that I /do/ have
		overlap_entities = OOBTree_intersection( incoming_entities, current_entities )

		# The weak refs we keep are non-persistent, so when we write out the tree set
		# we're going to write out all of the data anyway for every bucket that we touch.
		# So it makes as much sense to clear the treeset out and start from
		# scratch as it does to add and remove to bring into sync...plus it's a bit safer
		# if comparisons of the keys change over time.
		self._friends_wref_set.clear()
		for x in overlap_entities:
			self._friends_wref_set.add( nti_interfaces.IWeakRef( x ) )

		# Now actually Add the new ones so that we can fire the right events
		for x in missing_entities:
			result += self.addFriend( x )

		# Any extras that we used to have but tossed count towards our total
		result += len( OOBTree_difference( current_entities, incoming_entities ) )

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
			self.updateLastMod() # Sigh. Some general_purpose tests depend on this, regardless of whether any update got done.

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

@interface.implementer(nti_interfaces.IDynamicSharingTargetFriendsList)
class DynamicFriendsList(DynamicSharingTargetMixin,FriendsList): #order matters
	"""
	Something of a hack to introduce a dynamic, but iterable
	user-managed group/list.

	These are half FriendsList and half Community. When people are
	added to the list (and they don't get a veto), they are also added
	to the "community" that is this object, where it externalizes
	using its NTIID as 'Username' (since its local username is not
	unique) The NTIID is resolvable through Entity.get_entity like
	magic, so this object will magically start appearing for them, and
	also will be searchable by them.

	Targets not only don't get a say about being added to the group in
	the first place, they cannot exit it, as the external property
	that is "Communities" or "DynamicMemberships" is not currently
	editable. This could be implemented in a couple of ways, with the easiest
	being to simply make that property editable. Note however that they can
	stop following this DFL, cutting down on the visible noise.
	"""

	defaultGravatarType = 'retro'

	__external_class_name__ = 'FriendsList'
	#: Although this class itself cannot be directly created externally,
	#: the factory may change this. See :meth:`_FriendsListMap.external_factory`
	__external_can_create__ = False

	mime_type = 'application/vnd.nextthought.friendslist'

	# This object handle updating friends on creating/updating
	# An event (see sharing.py) handles when this object is deleted.
	# If 'Communities' becomes editable, then a new event would need to be
	# done to handle removing the friend in that case
	def _on_added_friend( self, friend ):
		assert self.creator, "Must have creator"
		super(DynamicFriendsList,self)._on_added_friend( friend )
		friend.record_dynamic_membership( self )
		friend.follow( self )

	def _update_friends_from_external( self, new_friends ):
		old_friends = set( self )
		super(DynamicFriendsList,self)._update_friends_from_external( new_friends )
		new_friends = set( self )

		# New additions would have been added, we only have to take care of
		# removals.
		ex_friends = old_friends - new_friends
		for i_hate_you in ex_friends:
			i_hate_you.record_no_longer_dynamic_member( self )
			i_hate_you.stop_following( self )

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
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
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
	"""
	Container class for :class:`FriendsList` objects.
	"""

	contained_type = nti_interfaces.IFriendsList
	container_name = 'FriendsLists'

	@classmethod
	def external_factory( cls, extDict ):
		"""
		Creates a new friends list.

		If the external dictionary has the ``IsDynamicSharing`` value set to true,
		then the friends list is a :class:`DynamicFriendsList`. This is necessary because
		externally we do not distinguish between the two classes for the sake of the UI.

		.. note:: This might need to change; this might in fact be a very bad idea. This
			bypasses any of the site or role-based object creation set up by nti.appserver;
			meaning that if we need to implement something like that we have to do it in a different
			fashion. This would be easier if the UI wanted to/was able to distinguish the two
			types of FLs.
		"""
		factory = FriendsList if not extDict.get( 'IsDynamicSharing' ) else DynamicFriendsList
		return factory( extDict['Username'] if 'Username' in extDict else extDict['ID'] )

nti_interfaces.IFriendsList.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
											Factory( _FriendsListMap.external_factory,
													 interfaces=(nti_interfaces.IFriendsList,)) )
