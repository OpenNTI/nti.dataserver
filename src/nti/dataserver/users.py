#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

import os

import numbers
import hashlib
import functools
import time

from zope import interface
from zope import component
from zope.component.factory import Factory

import persistent
from BTrees.OOBTree import OOTreeSet
import transaction
import UserList

import collections
import urllib

from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import ntiids
from nti.dataserver import enclosures
from nti.dataserver import links
from nti.dataserver import mimetype
from nti import apns

import nti.apns.interfaces


def _createAvatarURL( username, defaultGravatarType='mm' ):
	md5str = hashlib.md5( username.lower() ).hexdigest()
	result = 'http://www.gravatar.com/avatar/%s?s=128&d=%s' % (md5str,defaultGravatarType)
	return result

def _get_shared_dataserver(context=None,default=None):
	if default != None:
		return component.queryUtility( nti_interfaces.IDataserver, context=context, default=default )
	return component.getUtility( nti_interfaces.IDataserver, context=context )


def _downloadAvatarIcons( targetDir ):
	_users = [x for x in _get_shared_dataserver().root['users'].values()
				 if hasattr( x, 'username')]
	seen = set()
	def _downloadAvatarIcon( user, targetDir ):

		username = user.username if hasattr( user, 'username' ) else user
		if username in seen: return
		seen.add( username )
		md5str = hashlib.md5( username.lower() ).hexdigest()
		url = user.avatarURL if hasattr( user, 'avatarURL' ) else _createAvatarURL( username )
		url = url.replace( 'www.gravatar', 'lb.gravatar' )
		url = url.replace( 's=44', 's=128' )
		print username, url
		os.system( '/opt/local/bin/wget -q -O %s/%s "%s"' %(targetDir,md5str,url) )

	for user in _users:
		_downloadAvatarIcon( user, targetDir )
		if hasattr( user, 'friendsLists' ):
			for x in user.friendsLists.values():
				if not isinstance( x, Entity ):
					continue
				_downloadAvatarIcon( x, targetDir )
				for friend in x:
					_downloadAvatarIcon( friend, targetDir )


@functools.total_ordering
class Entity(persistent.Persistent,datastructures.CreatedModDateTrackingObject,datastructures.ExternalizableDictionaryMixin):
	"""
	The root for things that represent human-like objects.
	"""

	interface.implements( nti_interfaces.IEntity )

	@classmethod
	def get_entity( cls, username, dataserver=None, default=None, _namespace='users' ):
		"""
		Returns an existing entity with the given username or None. If the
		dataserver is not given, then the global dataserver will be used.
		"""
		# Allow for escaped usernames, since they are hard to defend against
		# at a higher level (this behaviour changed in pyramid 1.2.3)
		username = urllib.unquote( username )
		dataserver = dataserver or _get_shared_dataserver(default=default)
		if dataserver is not default:
			return dataserver.root[_namespace].get( username, default )
		return default

	creator = nti_interfaces.SYSTEM_USER_NAME
	__parent__ = None

	def __init__(self, username, avatarURL=None, realname=None, alias=None):
		super(Entity,self).__init__()
		if not username or '%' in username:
			# % is illegal because we sometimes have to
			# URL encode an @ to %40.
			raise ValueError( 'Illegal username ' + str(username) )

		self.username = username
		self._avatarURL = avatarURL
		self._realname = realname
		self._alias = alias
		# Entities, and in particular Principals, have a created time,
		# and their last modified date is initialized to this created
		# time...this implies there are never temporary objects of this type
		# and that this type represents a fully formed object after construction
		self.createdTime = self.updateLastMod()

	def _get__name__(self):
		return self.username
	def _set__name__(self,new_name):
		self.username = new_name
	__name__ = property(_get__name__, _set__name__ )


	def __repr__(self):
		return '%s("%s","%s","%s","%s")' % (self.__class__.__name__,self.username,self.avatarURL, self.realname, self.alias)

	def __str__(self):
		return self.username

	def _getAvatarURL(self):
		""" A string giving the URL for an image to be used
		for this object. May be a data: URL, may be a
		Gravatar URL. Will always be present. """
		result = getattr( self, '_avatarURL', None )
		if result is None:
			# Construct one using Gravatars
			result = _createAvatarURL( self.username, self.defaultGravatarType )

		return result

	def _setAvatarURL( self, url ):
		self._avatarURL = url

	avatarURL = property( _getAvatarURL, _setAvatarURL )

	# Subclasses or instances can set this to
	# request a different type
	defaultGravatarType = 'mm'

	def _getRealname(self):
		result = getattr(self, '_realname', None) or self.username
		if result is self.username:
			# Try to make it prettier.
			# Probably shouldn't do this in production.
			if '@' in result:
				result = self.username[0:self.username.index('@')]
				result = result.replace( '.', ' ' ).title()
		return result

	def _setRealname( self, value ):
		self._realname = value

	realname = property( _getRealname, _setRealname )

	def _getAlias(self):
		result =  getattr(self, '_alias', None)
		return result if result is not None else self.username

	def _setAlias( self, value ):
		self._alias = value

	alias = property( _getAlias, _setAlias )

	@property
	def preferredDisplayName( self ):
		if self.realname:
			return self.realname
		if self.alias:
			return self.alias
		return self.username

	@property
	def id(self):
		""" Our ID is a synonym for our username"""
		return self.username

	def get_by_ntiid( self, container_id ):
		"""
		Return something that belongs to this object based on looking
		up its NTIID, or None.
		"""
		assert ntiids.get_provider( container_id ) == self.username
		return None

	### Externalization ###

	def toExternalObject( self ):
		""" :return: The value of :meth:`toSummaryExternalObject` """
		result = self.toSummaryExternalObject()
		# restore last modified since we are the true representation
		result['Last Modified'] = getattr( self, 'lastModified', 0 )
		return result

	def toSummaryExternalObject( self ):
		"""
		:return: Standard dictionary minus Last Modified plus the properties of this class.
			These properties include 'Username', 'avatarURL', 'realname', and 'alias'.

		EOD
		"""
		extDict = super(Entity,self).toExternalDictionary( )
		# Notice that we delete the last modified date. Because this is
		# not a real representation of the object, we don't want people to cache based
		# on it.
		extDict.pop( 'Last Modified', None )
		extDict['Username'] = self.username
		extDict['avatarURL'] = self.avatarURL
		extDict['realname'] = self.realname
		extDict['alias'] = self.alias
		extDict['CreatedTime'] = getattr( self, 'createdTime', 42 ) # for migration
		return extDict

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		def setIf( name ):
			o = parsed.pop( name, None )
			if o is not None: setattr( self, name, o )

		setIf( 'realname' )
		setIf( 'alias' )
		setIf( 'avatarURL' )

	### Comparisons and Hashing ###

	def __eq__(self, other):
		return other != None and self.username == getattr(other, 'username', None)

	def __lt__(self, other):
		return self.username < other.username

	def __hash__(self):
		return self.username.__hash__()



class SharingTarget(Entity):
	"""
	Something that is a holder of shared data. These objects
	may be "passive."

	**Sharing Model**

	In general, the sharing relationship has to be consumated at both sides.
	Relationships are between the entity doing the sharing (the *source*),
	and the entity getting the shared data (the *target*) organizational
	structures within the source (e.g., *friends lists* are irrelevant. This
	relationship is called the *accepts* relationship.

	It is assumed that targets will accept shared data by default, but they
	may choose to opt out of any relationship. The opt out status of a
	target is retained so that future relationship requests from a
	previously opted-out entity are **not** accepted by default.

	Another relationship is the *follows* relationship. A source may share
	data with another source or with an entire community (such as
	*Everyone*). The follows relationship is relevant only for the latter
	situation. Follows relationships are between an entity and a community
	or specific source. When an entity follows a community, it receives
	everything shared with that community. When an entity follows an
	individual, it receives things shared by that individual *to communities
	the entity is a member of.* Note that follows is a one-way
	relationship. The source implicitly granted permission when it shared
	something with the community.

	"""

	MAX_STREAM_SIZE = 50

	def __init__( self, *args, **kwargs ):
		super(SharingTarget,self).__init__( *args, **kwargs )
		# Notice that I'm still working out
		# how best to reference other persistent objects, by
		# username/id or by weakrefs to the object itself. Thus
		# the inconsistencies.

		self._sources_not_accepted = OOTreeSet()
		"""
		Set us usernames we won't accept shared data from. Also applies to
		things pulled from communities.
		"""

		self._sources_accepted = OOTreeSet()
		"""
		Set of usernames that we'll accept explicitly shared data
		from. Notice that acceptance/not acceptance is completely on
		our side of things; the sender never knows--our 'ignore' is a
		quiet ignore.
		"""

		# For things that are shared explicitly with me, we maintain a structure
		# that parallels the contained items map. The first level is
		# from container ID to a list of weak references to shared objects.
		# (Un-sharing something, which requires removal from an arbitrary
		# position in the list, should be rare.) Notice that we must NOT
		# have the shared storage set or use IDs, because these objects
		# are not owned by us.
		# TODO: Specialize these data structures
		self.containersOfShared = datastructures.ContainedStorage( weak=True,
																   create=False,
																   containerType=datastructures.PersistentExternalizableList,
																   set_ids=False )

		# A cache of recent items that make of the stream. Going back
		# further than this requires walking through the containersOfShared.
		self.streamCache = datastructures.ModDateTrackingOOBTree()

	def __setstate__( self, state ):
		super(SharingTarget,self).__setstate__( state )
		if isinstance( getattr( self, '_sources_not_accepted', set() ), set ):
			self._sources_not_accepted = OOTreeSet( getattr( self, '_sources_not_accepted', set() ) )
		if isinstance( getattr( self, '_sources_accepted', set() ), set ):
			self._sources_accepted = OOTreeSet( getattr( self, '_sources_accepted', set() ) )
		if getattr( self.containersOfShared, 'set_ids', True ):
			# So in __setstate__, it's critical to not modify
			# other objects unless they require it.
			self.containersOfShared.set_ids = False

	def _discard( self, s, k ):
		try:
			s.remove( k )
			self._p_changed = True
		except KeyError: pass

	def accept_shared_data_from( self, source ):
		"""
		Begin accepting shared data from the `source`.

		If the `source` is being ignored, it will no longer be ignored.
		This method is usually called on this object by (on behalf of) `source`
		itself.
		This relationship persists until terminated, it doesn't cease simply
		because the `source` deleted the original friends list (circle).

		:returns: A truth value of whether or not we actually are now
			accepting shared data. This class always returns True if
			`source` is valid, subclasses may differ (this class doesn't
			implement ignoring).
		"""
		if not source: return False
		self._discard( self._sources_not_accepted,  source.username )
		self._sources_accepted.add( source.username )
		# FIXME: Why are we having to do this?
		self._p_changed = True
		return True

	def stop_accepting_shared_data_from( self, source ):
		if not source: return False
		self._discard( self._sources_accepted, source.username )
		return True

	@property
	def accepting_shared_data_from( self ):
		""" :returns: Iterable names of entities we accept shared data from. """
		return set(self._sources_accepted)

	def ignore_shared_data_from( self, source ):
		"""
		The opposite of :meth:`accept_shared_data_from`.

		This method is usually called on the object on behalf of this
		object (e.g., by the user this object represents).
		"""
		if not source: return False
		self._discard( self._sources_accepted, source.username )
		self._sources_not_accepted.add( source.username )
		self._p_changed = True
		return True

	def stop_ignoring_shared_data_from( self, source ):
		if not source: return False
		self._discard( self._sources_not_accepted, source.username )
		return True

	def reset_shared_data_from( self, source ):
		"""
		Stop accepting shared data from the `source`, but also do not ignore it.

		This method is usually called on the object on behalf of this
		object.

		:returns: A truth value of whether or not we accepted the
			reset. This implementation returns True if source is valid.
		"""
		if not source: return False
		self._discard( self._sources_accepted, source.username )
		self._discard( self._sources_not_accepted, source.username )

	def reset_all_shared_data( self ):
		"""
		Causes this object to forget all sharing and ignoring settings.
		"""
		# Keep the same objects in case of references
		self.reset_ignored_shared_data()
		self.reset_accepted_shared_data()

	def reset_ignored_shared_data( self ):
		"""
		Causes this object to forget all ignored settings.
		"""
		self._sources_not_accepted.clear()
		self._p_changed = True

	def reset_accepted_shared_data( self ):
		"""
		Causes this object to forget all accepted users.
		"""
		self._sources_accepted.clear()
		self._p_changed = True

	@property
	def ignoring_shared_data_from( self ):
		""" :returns: Iterable of names of entities we are specifically ignoring shared data from. """
		return set(self._sources_not_accepted)

	def is_accepting_shared_data_from( self, source ):
		"""
		Return if this object is accepting data that is explicitly
		shared with it by `source`.
		"""
		return (source.username if hasattr(source, 'username') else source) in self._sources_accepted

	def is_ignoring_shared_data_from( self, source ):
		"""
		The opposite of :meth:`is_accepting_shared_data_from`
		"""
		# Naturally we ignore ourself
		username = source.username if hasattr(source, 'username') else source
		return username == self.username or username in self._sources_not_accepted

	# TODO: In addition to the actual explicitly shared objects that I've
	# accepted because I'm not ignoring, we need the "incoming" group
	# for things I haven't yet accepted by are still shared with me.
	def getSharedContainer( self, containerId, defaultValue=() ):
		"""
		:return: If the containerId is found, an iterable of callable objects (weak refs);
			calling the objects will either return the actual shared object, or None.
		"""
		result = self.containersOfShared.getContainer( containerId, defaultValue )
		return result

	def _addSharedObject( self, contained ):
		self.containersOfShared.addContainedObject( contained )

	def _removeSharedObject( self, contained ):
		"""
		:return: The removed object, or None if nothing was removed.
		"""
		return self.containersOfShared.deleteEqualContainedObject( contained )

	def _addToStream( self, change ):
		container = self.streamCache.get( change.containerId )
		if container is None:
			container = datastructures.PersistentExternalizableWeakList()
			self.streamCache[change.containerId] = container
		if len(container) >= self.MAX_STREAM_SIZE:
			# TODO: O(n)
			container.pop( 0 )

		container.append( change )

	def _get_stream_cache_containers( self, containerId ):
		""" Return a sequence of stream cache containers for the id. """
		return (self.streamCache.get( containerId, () ),)

	def getContainedStream( self, containerId, minAge=0, maxCount=MAX_STREAM_SIZE ):
		# The contained stream is an amalgamation of the traffic explicitly
		# to us, plus the traffic of things we're following. We merge these together and return
		# just the ones that fit the criteria.
		# TODO: What's the right heuristic here? Seems like things shared directly with me
		# may be more important than things I'm following...
		# TODO: These data structures could and should be optimized for this.
		result = datastructures.LastModifiedCopyingUserList()

		containers = self._get_stream_cache_containers( containerId )

		def add( item, lm=None ):
			lm = lm or item.lastModified
			result.append( item )
			result.updateLastModIfGreater( lm )

		for container in containers:
			for item in container:
				if (item and item.lastModified > minAge
					and not self.is_ignoring_shared_data_from( item.creator ) ):
					add( item )

					if len( result ) > maxCount:
						return result

		# If we get here, then we weren't able to satisfy the request from the caches. Must walk
		# through the shared items directly.
		# We should probably be able to satisfy the request from the people we
		# follow. If not, we try to fill in with everything shared with us/followed by us
		# being careful to avoid duplicating things present in the stream
		# TODO: We've lost change information for these items.
		def dup( item ):
			for x in result:
				if x.object == item: return True
			return False
		for item in self.getSharedContainer( containerId ):
			# These items are callables, weak refs
			item = item()
			if item and item.lastModified > minAge and not dup( item ):
				change = Change( Change.SHARED, item )
				change.creator = item.creator or self

				# Since we're fabricating a change for this item,
				# we know it can be no later than when the item itself was last changed
				change.lastModified = item.lastModified

				add( change, item.lastModified )

				if len(result) > maxCount:
					break
		# We'll we've done the best that we can.
		return result

	def _acceptIncomingChange( self, change ):
		self._addToStream( change )
		# TODO: What's the right check here?
		if not isinstance( change.object, Entity ):
			self._addSharedObject( change.object )

	def _noticeChange( self, change ):
		""" Should run in a transaction. """
		# We hope to only get changes for objects shared with us, but
		# we double check to be sure--DELETES must always go through.

		if change.type in (Change.CREATED,Change.SHARED):
			if (change.object is not None
				and change.object.isSharedWith( self )
				and self.is_accepting_shared_data_from( change.creator )) :
				self._acceptIncomingChange( change )
		elif change.type == Change.MODIFIED:
			if change.object is not None:
				if change.object.isSharedWith( self ):
					# FIXME: We get duplicate shared objects
					# following multiple changes.
					self._addToStream( change )
					self._addSharedObject( change.object )
				else:
					# FIXME: Badly linear
					self._removeSharedObject( change.object )
		elif change.type == Change.DELETED:
			# The weak refs would clear eventually.
			# For speedy deletion at the expense of scale, we
			# can force the matter
			removed = self._removeSharedObject( change.object )
			if removed is False or removed is None: # Explicit, not falsey
				logger.warn( "Incoming deletion for object not found %s", change )
		elif change.type == Change.CIRCLED:
			self._acceptIncomingChange( change )

	@classmethod
	def onChange( cls, datasvr, msg, username=None, broadcast=None, **kwargs ):
		if username and not broadcast:
			logger.debug( 'Incoming change to %s', username )
			with datasvr.dbTrans():
				cls.get_entity( username, dataserver=datasvr )._noticeChange( msg )



class SharingSource(SharingTarget):
	"""
	Something that can share data. These objects are typically
	"active."
	"""

	def __init__( self, *args, **kwargs ):
		super(SharingSource,self).__init__( *args, **kwargs )
		# Notice that I'm still working out
		# how best to reference other persistent objects, by
		# username/id or by weakrefs to the object itself. Thus
		# the inconsistencies.

		self._communities = OOTreeSet()
		"""
		Set of usernames of communities we belong to.
		"""

		self._following = OOTreeSet()
		"""
		Set of entity names we want to follow.

		For users, we will source data specifically
		from them out of communities we belong to. For communities, we will
		take all data (with the exception of _sources_not_accepted, of course.
		"""

	def __setstate__(self, state ):
		super(SharingSource,self).__setstate__( state )
		if isinstance( getattr( self, '_communities', set() ), set ):
			self._communities = OOTreeSet()
		if isinstance( getattr( self, '_following', set() ), set ):
			self._following = OOTreeSet()

	def follow( self, source ):
		""" Adds `source` to the list of followers. """
		self._following.add( source.username )
		return True

	@property
	def following(self):
		""" :returns: Iterable names of entities we are following. """
		return set(self._following)

	def join_community( self, community ):
		""" Marks this object as a member of `community.` Does not follow `community`.
		:returns: Whether we are now following the community. """
		self._communities.add( community.username )
		return True

	@property
	def communities( self ):
		""" :returns: Iterable names of communities we belong to. """
		return set(self._communities)

	def _get_stream_cache_containers( self, containerId ):
		# start with ours
		result = [self.streamCache.get( containerId, () )]

		# add everything we follow. If it's a community, we take the
		# whole thing (ignores are filtered in the parent method). If
		# it's a person, we take stuff they've shared to communities
		# we're a member of

		persons_following = []
		for following in self._following:
			following = self.get_entity( following )
			if following is None: continue
			if isinstance( following, DynamicSharingTarget ):
				result += following._get_stream_cache_containers( containerId )
			else:
				persons_following.append( following )

		for comm in self._communities:
			comm = self.get_entity( comm )
			if comm is None: continue
			result.append( [x for x in comm.streamCache.get( containerId, () )
							if x is not None and x.creator in persons_following] )


		return result

	def getSharedContainer( self, containerId, defaultValue=() ):
		# start with ours
		result = datastructures.LastModifiedCopyingUserList()
		super_result = super(SharingSource,self).getSharedContainer( containerId, defaultValue=defaultValue )
		if super_result is not None and super_result is not defaultValue:
			result.extend( super_result )

		# add everything we follow. If it's a community, we take the whole
		# thing (minus ignores). If it's a person, we take stuff they've shared to
		# communities we're a member of (ignores not an issue).
		# Note that to be consistent with the super class interface, we do not
		# de-ref the weak refs in the returned value (even though we must de-ref them
		# internally)
		# TODO: This needs much optimization. And things like paging will
		# be important.

		persons_following = []
		communities_seen = []
		for following in self._following:
			following = self.get_entity( following )
			if following is None: continue
			if isinstance( following, DynamicSharingTarget ):
				communities_seen.append( following )
				for ref in following.getSharedContainer( containerId ):
					x = ref()
					if x is not None and not self.is_ignoring_shared_data_from( x.creator ):
						result.append( ref )
						result.updateLastModIfGreater( x.lastModified )
			else:
				persons_following.append( following )

		for comm in self._communities:
			comm = self.get_entity( comm )
			if comm is None or comm in communities_seen: continue
			for ref in comm.getSharedContainer( containerId ):
				x = ref()
				if x and x.creator in persons_following:
					result.append( ref )
					result.updateLastModIfGreater( x.lastModified )

		# If we made no modifications, return the default
		# (which would have already been returned by super; possibly it returned other data)
		if not result:
			return super_result
		return result


class Principal(SharingSource):
	""" A Principal represents a set of credentials that has access to the system.
	One property is username."""

	def __init__(self, username=None, avatarURL=None, password='temp001',realname=None):
		super(Principal,self).__init__(username,avatarURL,realname=realname)
		if not username or '@' not in username:
			raise ValueError( 'Illegal username ' + username )

		self.password = password

class DynamicSharingTarget(SharingTarget):
	"""
	Instances represent communities or collections (e.g., tags)
	that a user might want to 'follow' or subscribe to.

	Since they don't represent individuals, they always accept 'subscribe'
	requests. They also don't generate any notifications.
	"""

	defaultGravatarType = 'retro'

	MAX_STREAM_SIZE = 100000
	# Turns out we need to maintain both the stream and the objects.
	def __init__(self, *args, **kwargs):
		super(DynamicSharingTarget,self).__init__( *args, **kwargs )


class Community(DynamicSharingTarget):

	# We override these methods for space efficiency.
	# TODO: Should we track membership here? If so, membership
	# would be a prereq for accepting shared data. Also,
	# Everyone would need these methods to return True
	def accept_shared_data_from( self, source ):
		return True

	def ignore_shared_data_from( self, source ):
		return False

	def is_accepting_shared_data_from( self, source ):
		return True

class Everyone(Community):
	""" A community that represents the entire world. """
	__external_class_name__ = 'Community'
	def __init__(self):
		super(Everyone,self).__init__( 'Everyone' )
		self.realname = 'Everyone'
		self.alias = 'Public'
		self.avatarURL = 'http://www.gravatar.com/avatar/dfa1147926ce6416f9f731dcd14c0260?s=128&d=retro'


EVERYONE_PROTO = Everyone()
EVERYONE = EVERYONE_PROTO
#""" There is only one Everyone community. """

class FriendsList(enclosures.SimpleEnclosureMixin,Entity): #Mixin order matters for __setstate__
	""" A FriendsList or Circle belongs to a user and
	contains references (strings or weakrefs to principals) to other
	users. It has a name and ID, possibly a custom image.

	All mutations to the list must go through the APIs of this class. """

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	defaultGravatarType = 'wavatar'
	__external_can_create__ = True

	interface.implements(nti_interfaces.IFriendsList,nti_interfaces.ISimpleEnclosureContainer)

	def __init__(self, username=None, avatarURL=None):
		super(FriendsList,self).__init__(username, avatarURL)
		self._friends = None

	def _on_added_friend( self, friend ):

		if isinstance( friend, SharingSource ):
			friend.accept_shared_data_from( self.creator )
			self.creator.follow( friend )

	def _resolve_friend( self, friend, ix ):
		result = friend
		if isinstance( friend, basestring ):
			result = User.get_user( friend, default=friend )
			if result is not friend:
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

	def __iter__(self):
		"""
		Iterating over a FriendsList iterates over its friends
		(as Entity objects), resolving weak refs.
		"""
		resolved = [self._resolve_friend(self.friends[i], i) for i in xrange(len(self.friends))]
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

		if self._friends is None: self._friends = datastructures.PersistentExternalizableList()
		if isinstance( friend, FriendsList ):
			# Recurse to generate the correct notifications
			for other_friend in friend.friends:
				self.addFriend( other_friend )
		elif isinstance( friend, Entity ):
			self._friends.append( persistent.wref.WeakRef( friend ) )
		elif isinstance( friend, collections.Mapping ) and 'Username' in friend:
			# Dictionaries and Dictionary-like things come in from
			# external representations. Resolve, then append.
			self.addFriend( User.get_user( friend['Username'], default=friend['Username'] ) )
		elif isinstance( friend, basestring ):
			# Try to resolve, add the resolved if possible, otherwise add the
			# string as a placeholder. Don't recurse, could be infinite
			friend = User.get_user( friend, default=friend )
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

	#### Externalization/Pickling

	def __setstate__( self, state ):
		super(FriendsList,self).__setstate__( state )
		if 'containerId' in self.__dict__:
			del self.__dict__['containerId']

	def get_containerId( self ):
		return 'FriendsLists'
	def set_containerId( self, cid ):
		pass
	containerId = property( get_containerId, set_containerId )


	def toExternalObject(self):
		extDict = super(FriendsList,self).toExternalObject()
		theFriends = []
		for friend in iter(self): #iter self to weak refs and dups
			if isinstance( friend, Entity ):
				if friend == self.creator:
					friend = friend.toPersonalSummaryExternalObject()
				else:
					friend = friend.toSummaryExternalObject()
			elif isinstance( friend, basestring ):
				friend = { 'Class': 'UnresolvedFriend',
						   'Username': friend,
						   'avatarURL' : _createAvatarURL( friend, SharingTarget.defaultGravatarType ) }
			else:
				friend = datastructures.toExternalObject( friend )
			theFriends.append( friend )

		extDict['friends'] = theFriends

		return extDict

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(FriendsList,self).updateFromExternalObject( parsed, *args, **kwargs )
		newFriends = parsed.pop('friends', None)
		# Update, as usual, starts from scratch.
		# Notice we allow not sending friends to easily change
		# the realname, alias, etc
		if newFriends is not None:
			self._friends = None
			for newFriend in newFriends:
				if isinstance( newFriend, basestring ) and isinstance(self.creator, User):
					otherList = self.creator.getFriendsList( newFriend )
					if otherList: newFriend = otherList
				self.addFriend( newFriend )

		if self.username is None:
			self.username = parsed.get( 'Username' )
		if self.username is None:
			self.username = parsed.get( 'ID' )

	@classmethod
	def _resolve_friends( cls, dataserver, parsed, externalFriends ):
		result = []
		for externalFriend in externalFriends:
			result.append( cls.get_entity( externalFriend, dataserver=dataserver, default=externalFriend ) )
		return result

	__external_resolvers__ = {'friends': _resolve_friends }


	def __eq__(self,other):
		result = super(FriendsList,self).__eq__(other)
		if result:
			result = self.friends == getattr(other, 'friends', None)
		return result
	def __lt__(self,other):
		result = super(FriendsList,self).__lt__(other)
		if result:
			result = self.friends < other.friends
		return result

class ShareableMixin(datastructures.CreatedModDateTrackingObject):
	""" Represents something that can be shared. It has a set of SharingTargets
	with which it is shared (permissions) and some flags. Only its creator
	can alter its sharing targets. It may be possible to copy this object. """

	def __init__( self ):
		super(ShareableMixin,self).__init__()
		# Our set of targets we are shared with. If we
		# have a creator, then only the creator can alter these.
		self._sharingTargets = None

	@property
	def sharingTargets(self):
		return self._sharingTargets if self._sharingTargets is not None else ()

	def clearSharingTargets( self ):
		self._sharingTargets = None
		self.updateLastMod()

	def addSharingTarget( self, target, actor=None ):
		""" Adds a sharing target. We accept either SharingTarget
		subclasses, or strings, or iterables of strings."""
		if isinstance( target, collections.Iterable ) \
			   and not isinstance( target, basestring ) \
			   and not hasattr( target, 'username' ):
			# expand iterables now
			for t in target: self.addSharingTarget( t, actor=actor )
			return

		if self.creator is not None and self.creator != actor:
			raise ValueError( "Creator (%s) is not actor (%s)" % (self.creator,actor) )
		if self._sharingTargets is None:
			self._sharingTargets = datastructures.PersistentExternalizableList()
		if target not in self._sharingTargets:
			# Don't allow sharing with ourself, it's weird
			# Allow self.creator to be  string or an Entity
			if not self.creator or (self.creator != target
									and getattr(self.creator, 'username', self.creator) != target):
				self._sharingTargets.append( target )
		# if we ourselves are persistent, mark us changed
		if hasattr( self, '_p_changed' ):
			setattr( self, '_p_changed', True )

		self.updateLastMod()

	def isSharedWith( self, wants ):
		""" Checks if we are shared with `wants`, which can be a
		Principal or a string."""
		if not self._sharingTargets:
			return False

		if not isinstance( wants, basestring ):
			# because our list has strings in it,
			# it's easiest to get this as a string now
			wants = wants.username

		return wants in self.getFlattenedSharingTargetNames()

	def getFlattenedSharingTargetNames(self):
		""" Returns a flattened :class:`set` of :class:`SharingTarget` usernames with whom this item
		is shared."""
		sharingTargetNames = set()

		def addToSet( target ):
			if isinstance( target, basestring ):
				sharingTargetNames.add( target )
			elif isinstance( target, collections.Iterable ):
				for x in target: addToSet( x )
			else:
				sharingTargetNames.add( target.username )

		for target in self.sharingTargets:
			addToSet( target )

		return sharingTargetNames

from activitystream_change import Change


@functools.total_ordering
class Device(persistent.Persistent,datastructures.CreatedModDateTrackingObject):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements( nti_interfaces.IDevice )
	__external_can_create__ = True

	def __init__(self, deviceId):
		super(Device,self).__init__()
		self.id = deviceId
		# device id arrives in hex encoding
		self.deviceId = deviceId.decode( 'hex' )

	def __setstate__( self, state ):
		super(Device,self).__setstate__( state )
		if 'containerId' in self.__dict__:
			del self.__dict__['containerId']

	def get_containerId( self ):
		return _DevicesMap.container_name
	def set_containerId( self, cid ):
		pass
	containerId = property( get_containerId, set_containerId )

	# We are disguising the very existence of this class.
	# That needs to change.
	def toExternalObject(self):
		return self.id

	def updateFromExternalObject(self,ext):
		pass

	def __eq__(self, other):
		return self.deviceId == getattr(other, 'deviceId', None)

	def __lt__(self, other):
		return self.deviceId < other.deviceId

	def __hash__(self):
		return self.deviceId.__hash__()

class _FriendsListMap(datastructures.AbstractNamedContainerMap):

	contained_type = nti_interfaces.IFriendsList
	container_name = 'FriendsLists'


nti_interfaces.IFriendsList.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
											Factory( lambda extDict:  FriendsList( extDict['Username'] if 'Username' in extDict else extDict['ID'] ),
													 interfaces=(nti_interfaces.IFriendsList,)) )

class _DevicesMap(datastructures.AbstractNamedContainerMap):

	contained_type = nti_interfaces.IDevice
	container_name = 'Devices'

	def __setitem__( self, key, value ):
		if not isinstance( value, Device ):
			value = Device( value )
		super(_DevicesMap,self).__setitem__( key, value )


nti_interfaces.IDevice.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
									   Factory( lambda extDict:  Device( extDict ),
												interfaces=(nti_interfaces.IDevice,)) )


class _TranscriptsMap(datastructures.AbstractNamedContainerMap):

	contained_type = nti_interfaces.ITranscript
	container_name = 'Transcripts'


class User(Principal):
	"""A user is the central class for data storage. It maintains
	not only a few distinct pieces of data but also a collection of
	Contained items.

	All additions and deletions to Contained items
	go through the User class, which takes care of posting appropriate
	notifications to queues. For updates to contained objects,
	the methods beginUpdates() and endUpdates() must surround the updates. Objects
	retreived from getObject() will be monitored for changes during this period
	and notifications posted at the end. Mutations to non-persistent data structurs
	may not be caught by this and so such objects should be explicitly marked
	as changed using setPersistentStateChanged() or this object's didUpdateObject()
	method. """

	interface.implements(nti_interfaces.IContainerIterable,
						 nti_interfaces.IUser)

	@classmethod
	def get_user( cls, username, dataserver=None, default=None ):
		""" Returns the User having `username`, else None. """
		result = cls.get_entity( username, dataserver=dataserver, default=default )
		return result if isinstance( result, User ) else default

	@classmethod
	def create_user( cls, dataserver=None, **kwargs ):
		""" Creates (and returns) and places in the dataserver a new user,
		constructed using the keyword arguments given, the same as those
		the User constructor takes. Overwrites an existing user. You handle
		the transaction.
		"""
		dataserver = dataserver or _get_shared_dataserver()
		user = cls( **kwargs )
		dataserver.root['users'][user.username] = user
		# When we auto-create users, we need to be sure
		# they have a database connection so that things that
		# are added /to them/ (their contained storage) in the same transaction
		# will also be able to get a database connection and hence
		# an OID.
		dataserver.root['users']._p_jar.add( user )

		return user

	# External incoming ignoring and accepting can arrive in three ways.
	# As a list, which replaces the entire contents.
	# As a single string, which is added to the list.
	# As a dictionary with keys 'add' and 'remove', mapping to lists

	@classmethod
	def _resolve_entities( cls, dataserver, external_object, value ):
		result = []
		if isinstance( value, basestring ):
			result = cls.get_entity( value, dataserver=dataserver )
		elif isinstance( value, collections.Sequence ):
			# A list of names or externalized-entity maps
			result = []
			for username in value:
				if isinstance(username, collections.Mapping):
					username = username.get( 'Username' )
				entity = cls.get_entity( username, dataserver=dataserver )
				if entity: result.append( entity )
		elif isinstance( value, collections.Mapping ):
			if value.get( 'add' ) or value.get( 'remove' ):
				# Specified edits
				result = { 'add': cls._resolve_entities( dataserver, external_object, value.get( 'add' ) ),
						   'remove': cls._resolve_entities( dataserver, external_object, value.get( 'remove' ) ) }
			else:
				# a single externalized entity map
				result = cls.get_entity( value.get( 'Username' ), dataserver=dataserver )

		return result

	__external_resolvers__ = { 'ignoring': _resolve_entities, 'accepting': _resolve_entities }
	__conflict_max_keys__ = ['lastLoginTime']
	__conflict_max_keys__.extend( Principal.__conflict_max_keys__ )
	__conflict_merge_keys__ = ['notificationCount']
	__conflict_merge_keys__.extend( Principal.__conflict_merge_keys__ )


	# TODO: If no AvatarURL is set when externalizing,
	# send back a gravatar URL for the primary email:
	# http://www.gravatar.com/avatar/%<Lowercase hex MD5>=44&d=mm

	def __init__(self, username, avatarURL=None, password='temp001',realname=None):
		super(User,self).__init__(username, avatarURL, password,realname=realname)
		# We maintain a Map of our friends lists, organized by
		# username (only one friend with a username)
		self.friendsLists = _FriendsListMap()

		# We have a default friends list called Public that
		# contains Public. It's a real list so the user
		# can delete it or change it.
		# TODO: To make getting it back easy, we need the
		# notion of 'suggested' entities to follow/share with
		# TODO: At some place we'll need to have different defaults for
		# different users (e.g., in a school, maybe the pre-defined list
		# is the class
		publicList = FriendsList( 'Everyone' )
		publicList.alias = 'Public'
		publicList.realname = 'Everyone'
		publicList.avatarURL = 'http://www.gravatar.com/avatar/dfa1147926ce6416f9f731dcd14c0260?s=128&d=retro'
		publicList.addFriend( EVERYONE )
		self.friendsLists['Everyone'] = publicList

		# Join our default community
		self.join_community( EVERYONE )

		# We maintain a list of devices associated with this user
		# TODO: Want a persistent set?
		self.devices = _DevicesMap()

		self.containers = datastructures.ContainedStorage(create=self,
														  containersType=datastructures.KeyPreservingCaseInsensitiveModDateTrackingOOBTree,
														  containers={self.friendsLists.container_name: self.friendsLists,
																	  self.devices.container_name: self.devices })
		self.__install_container_hooks()

		# The last login time is an number of seconds (as with time.time).
		# When it gets reset, the number of outstanding notifications also
		# resets. It is writable, number is not
		self.lastLoginTime = 0
		self.notificationCount = 0

		# We maintain our own stream. The modification queue posts
		# items to our stream, we are responsible for organization,
		# expiration, etc.
		self.stream = None

		# For begin/end update pairs we track a depth and we also
		# record all objects we hand out during this time, posting
		# notifications only on the last endUpdates
		self._v_updateDepth = 0
		self._v_updateSet = None

	def __install_container_hooks(self):
		self.containers.afterAddContainedObject = self._postCreateNotification
		self.containers.afterDeleteContainedObject = self._postDeleteNotification
		self.containers.afterGetContainedObject = self._trackObjectUpdates

	def _p_resolveConflict(self, oldState, savedState, newState):
		return super(User,self)._p_resolveConflict( oldState, savedState, newState )

	def __setstate__( self, state ):
		super(User,self).__setstate__( state )
		# re-install our hooks that are transient
		self.__install_container_hooks()
		# Default some possibly missing attributes.
		for k in ('lastLoginTime', 'notificationCount' ):
			if not hasattr( self, k ):
				setattr( self, k, 0 )
		# Make devices be the right class
		if self.devices.__class__ != _DevicesMap:
			self.devices.__class__ = _DevicesMap
		# Make containers actually be containers
		if not hasattr( self.containers, 'containers' ):
			self.containers = datastructures.ContainedStorage(create=self,
															  containersType=datastructures.KeyPreservingCaseInsensitiveModDateTrackingOOBTree,
															  containers={self.friendsLists.container_name: self.friendsLists,
																		  self.devices.container_name: self.devices })
		# Make containers case-insensitive
		# (Necessary to create by class name from mime types)
		if not isinstance( self.containers.containers, datastructures.KeyPreservingCaseInsensitiveModDateTrackingOOBTree ):
			self.containers.containers = datastructures.KeyPreservingCaseInsensitiveModDateTrackingOOBTree( self.containers.containers )

	@property
	def creator(self):
		""" For security, we are always our own creator. """
		return self

	@creator.setter
	def creator( self, other ):
		""" Ignored. """
		return

	@property
	def containerId(self):
		return "Users"

	@property
	def presence( self ):
		"""Returns an indicator of the user's current presence in the system."""
		return "Offline"

	### Externalization

	def toSummaryExternalObject( self ):
		extDict = super(User,self).toSummaryExternalObject( )

		# TODO: Is this a privacy concern?
		extDict['lastLoginTime'] = self.lastLoginTime
		extDict['NotificationCount'] = self.notificationCount
		# TODO: Presence information will depend on who's asking
		extDict['Presence'] = self.presence
		return extDict

	def toPersonalSummaryExternalObject( self ):
		"""
		:return: the externalization intended to be sent when requested by this user.
		"""

		# Super's toExternalObject is defined to use toSummaryExternalObject
		# so we get lastLoginTime and NotificationCount from there.
		extDict = super(User,self).toExternalObject()
		def ext( l ):
			result = []
			for name in l:
				e = self.get_entity( name )
				if e:
					result.append( e.toSummaryExternalObject() )
			return result

		# Communities are not currently editable,
		# and will need special handling of Everyone
		extDict['Communities'] = ext(self.communities)
		# Following is writable
		extDict['following'] = ext(self.following)
		# as is ignoring and accepting
		extDict['ignoring'] = ext(self.ignoring_shared_data_from)
		extDict['accepting'] = ext(self.accepting_shared_data_from)
		extDict['Links'] = [ links.Link( datastructures.to_external_ntiid_oid( self ), rel='edit' ) ]
		return extDict

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		with self._NoChangeBroadcast( self ):
			super(User,self).updateFromExternalObject( parsed, *args, **kwargs )
			lastLoginTime = parsed.pop( 'lastLoginTime', None )
			if isinstance( lastLoginTime, numbers.Number ) and self.lastLoginTime < lastLoginTime:
				self.lastLoginTime = lastLoginTime
				self.notificationCount = 0

			if 'password' in parsed:
				password = parsed.pop( 'password' )
				self.password = password

			# These two arrays cancel each other out. In order to just have to
			# deal with sending one array or the other, the presence of an entry
			# in one array will remove it from the other. This happens

			# See notes on how ignoring and accepting values may arrive
			def handle_ext( resetAll, reset, add, remove, value ):
				if isinstance( value, collections.Sequence ):
					# replacement list
					resetAll()
					for x in value:
						reset( x )
						add( x )
				elif isinstance( value, collections.Mapping ):
					# adds and removes
					# Could be present but None, so be explicit about default
					for x in (value.get( 'add' ) or ()):
						reset( x )
						add( x )
					for x in (value.get( 'remove') or () ):
						remove( x )
				elif value is not None:
					# One to add
					reset( x )
					add( value )


			# These two arrays cancel each other out. In order to just have to
			# deal with sending one array or the other, the presence of an entry
			# in one array will remove it from the other. This happens
			# automatically for ignores, but because the implicit calls
			# to accept shared data ignore those in the ignore list (in our implementation)
			# we must manually make this happen for that list.
			ignoring = parsed.pop( 'ignoring', None )
			handle_ext( self.reset_ignored_shared_data,
						self.reset_shared_data_from,
						self.ignore_shared_data_from,
						self.stop_ignoring_shared_data_from,
						ignoring )

			accepting = parsed.pop( 'accepting', None )
			handle_ext( self.reset_accepted_shared_data,
						self.reset_shared_data_from,
						self.accept_shared_data_from,
						self.stop_accepting_shared_data_from,
					accepting )
			self.updateLastMod()

	def toExternalObject( self ):
		if hasattr( self, '_v_writingSelf' ):
			return self.username
		setattr( self, '_v_writingSelf', True )
		try:
			extDict = self.toPersonalSummaryExternalObject()
			for k,v in self.containers.iteritems():
				extDict[k] = datastructures.toExternalObject( v )
		finally:
			delattr( self, '_v_writingSelf' )
		return extDict

	### Sharing

	def accept_shared_data_from( self, source ):
		""" Accepts if not ignored; auto-follows as well.
		:return: A truth value. If this was the initial add, it will be the Change.
			If the source is ignored, it will be False."""
		if self.is_ignoring_shared_data_from( source ):
			return False
		already_accepting = super(User,self).is_accepting_shared_data_from( source )
		if super(User,self).accept_shared_data_from( source ):
			if already_accepting:
				# No change
				return True

			# Broadcast a change for the first time we're circled by this person
			# TODO: Do we need to implement a limbo state, pending acceptance
			# by the person?
			change = Change( Change.CIRCLED, source )
			change.creator = source
			change.containerId = '' # Not anchored, show at root and below
			change.useSummaryExternalObject = True # Don't send the whole user
			self._broadcast_change_to( change, username=self.username )
			return change # which is both True and useful

	def is_accepting_shared_data_from( self, source ):
		""" We say we're accepting so long as we're not ignoring. """
		# TODO: the 'incoming' group discussed in super will obsolete this
		return not self.is_ignoring_shared_data_from( source )

	def getFriendsList( self, name ):
		""" Returns the friends list having the given name, otherwise
		returns None. """
		return self.friendsLists.get( name )

	def maybeCreateContainedObjectWithType( self, datatype, externalValue ):
		if datatype == 'Devices':
			result = Device(externalValue)
		else:
			result = self.containers.maybeCreateContainedObjectWithType( datatype, externalValue )
		return result

	def addContainedObject( self, contained ):
		# Must make sure it has a connection so it can generate
		# a OID/ID. We must use our connection, rather than
		# our storage's connection because if we were created
		# in the current transaction, our storage will not
		# have a connection (and adding the connection in
		# addition to the user in User.create_user fails later
		# on with spurious POSKeyError).
		if getattr( contained, '_p_jar', self ) is None \
			and getattr( self, '_p_jar' ) is not None:
			self._p_jar.add( contained )

		result = self.containers.addContainedObject( contained )
		return result

	def _postCreateNotification( self, obj ):
		self._postNotification( Change.CREATED, obj )

	def _postDeleteNotification( self, obj ):
		self._postNotification( Change.DELETED, obj )
		# A delete notification trumps any other modifications that
		# might be pending (otherwise we can wind up with weird scenarios
		# for modification notifications /after/ a delete)
		if getattr( self, '_v_updateSet', None ) is not None:
			self._v_updateSet = [x for x in self._v_updateSet
								 if ( isinstance(x,tuple) and x[0] != obj ) or (not isinstance(x,tuple) and x != obj)]

	def deleteContainedObject( self, containerId, containedId ):
		return self.containers.deleteContainedObject( containerId, containedId )

	# TODO: Could/Should we use proxy objects to automate
	# the update process? Allowing updates directly to deep objects?
	# What about monitoring the resources associated with the transaction
	# and if any of them belong to us posting a notification? (That seems
	# convenient but a poor separation of concerns)

	def get_by_ntiid( self, container_id ):
		result = super(User,self).get_by_ntiid( container_id )
		if not result:
			if ntiids.is_ntiid_of_type( container_id, ntiids.TYPE_MEETINGROOM ):
			# TODO: Generalize this
			# TODO: Should we track updates here?
				for x in self.friendsLists.itervalues():
					if getattr( x, 'NTIID', None ) == container_id:
						result = x
						break
			elif ntiids.is_ntiid_of_type( container_id, ntiids.TYPE_TRANSCRIPT ):
				# TODO: We shouldn't know about transcript summary storage.
				# This is too closely coupled to chat_transcripts. I could use
				# an adapter from this to...something, or a utility that takes this
				# (and possibly the NTIIDs). Not sure how much better that is, since
				# it still funnels through this object.
				ntiid_summary = ntiids.make_ntiid( base=container_id,
												   provider=nti_interfaces.SYSTEM_USER_NAME,
												   nttype=ntiids.TYPE_OID )
				meeting = _get_shared_dataserver().get_by_oid( ntiid_summary )
				result = self.getContainedObject( meeting.containerId,
												  ntiids.make_ntiid( base=container_id, nttype=ntiids.TYPE_TRANSCRIPT_SUMMARY ) )
				result = nti_interfaces.ITranscript(result)
			else:
				# Try looking up the ntiid by name in each container
				# TODO: This is terribly expensive
				for container_name in self.containers.containers:
					container = self.containers.containers[container_name]
					if isinstance( container, numbers.Number ): continue
					result = container.get( container_id )
					if result:
						break
		return result

	def getContainedObject( self, containerId, containedId, defaultValue=None ):
		if containerId == self.containerId: # "Users"
			return self
		# TODO Unify this.
		if containerId == _TranscriptsMap.container_name:
			# FIXME: Total hack, like getContainer
			transcript = _get_shared_dataserver().chatserver.transcript_for_user_in_room( self.username, containedId )
			return transcript or defaultValue
		return self.containers.getContainedObject( containerId, containedId, defaultValue )

	def getContainer( self, containerId, defaultValue=None ):
		# TODO: Unify again
		if containerId == _TranscriptsMap.container_name:
			# FIXME: This is obviously a quick hack with no thought
			# given to performance.
			class FakeTranscripts(object):
				def __init__( self, u ):
					self.username = u
					self.lastModified = 0
					# capture this in the transaction.
					self.summaries = _get_shared_dataserver().chatserver.list_transcripts_for_user( self.username )

				def get( self, key, defaultValue=None ):
					for summary in self.summaries:
						if summary.RoomInfo.ID == key:
							return summary
						return defaultValue

				def iteritems(self):
					return iter( {summary.RoomInfo.ID: summary for summary in self.summaries} )
				def iterkeys(self):
					return iter( [k for k in self.iteritems()] )
				def __iter__( self ):
					return self.iterkeys()
				def __contains__( self, key ):
					return key in list(self.iterkeys())
				def toExternalObject( self ):
					return datastructures.toExternalObject( self.summaries )
			return FakeTranscripts(self.username)

		stored_value = self.containers.getContainer( containerId, defaultValue )
		return stored_value


	def getAllContainers( self ):
		""" Returns all containers, as a map from containerId to container.
		The returned value MOST NOT be modified."""
		return self.containers.containers

	def _is_container_ntiid( self, containerId ):
		"""
		Filters out things that are not used as NTIIDs. In the future,
		this will be easy (as soon as everything is tag-based). Until then,
		we rely on the fact that all our custom keys are upper cased.
		"""
		return len(containerId) > 1 and \
			   (containerId.startswith( 'tag:nextthought.com' )
				or containerId[0].islower())

	def iterntiids( self ):
		"""
		Returns an iterable across the NTIIDs that are relevant to this user.
		"""
		owned = [k for k in self.containers if self._is_container_ntiid( k )]
		shared = [k for k in self.containersOfShared if self._is_container_ntiid( k )]
		return iter( set( owned ) | set( shared ) )

	def itercontainers( self ):
		# TODO: Not sure about this. Who should be responsible for
		# the UGD containers? Should we have some different layout
		# for that (probably).
		return (self.containers.containers[k]
				for k in self.containers.containers
				if nti_interfaces.INamedContainer.providedBy( self.containers.containers[k] ) )

	def beginUpdates(self):
		# Because the container hooks are volatile, the container object
		# could have been 'ghosted' and lost these hooks before we
		# got here. Thus, we must take care to re-activate it, or
		# else our hooks and change tracking won't fire.
		self.__install_container_hooks()
		if not hasattr( self, '_v_updateDepth' ):
			self._v_updateDepth = 0 # TODO: Thread local
		self._v_updateDepth += 1
		if self._v_updateDepth == 1:
			# it would be nice to use a set, but
			# we're not guaranteed to have hashable objects
			self._v_updateSet = list()
		return self

	def _trackObjectUpdates( self, obj ):
		if hasattr( self, '_v_updateSet' ) and getattr(self, '_v_updateSet' ) is not None:
			if not isinstance( obj, persistent.Persistent ):
				if isinstance( obj, collections.Sequence ):
					for x in obj: self._trackObjectUpdates( x )
				elif isinstance( obj, collections.Mapping ):
					for x in obj.itervalues(): self._trackObjectUpdates( x )
			# The updateSet consists of either the object, or, if it as a
			# shared object, (object, sharedSet). This allows us to be
			# smart about how we distribute notifications.
			self._v_updateSet.append( (obj,obj.getFlattenedSharingTargetNames())
									  if isinstance( obj, ShareableMixin)
									  else obj )

	def didUpdateObject( self, *objs ):
		if getattr(self, '_v_updateDepth', 0) > 0:
			for obj in objs:
				datastructures.setPersistentStateChanged( obj )
				self._trackObjectUpdates( obj )

	def endUpdates(self):
		""" Commits any outstanding transaction and posts notifications
		referring to the updated objects. """
		if not hasattr(self, '_v_updateSet') or not hasattr(self,'_v_updateDepth'):
			logger.warn( 'Update depth inconsistent' )
			return
		self._v_updateDepth -= 1
		if self._v_updateDepth <= 0:
			self._v_updateDepth = 0
			end_time = time.time() # Make all the modification times consistent
			for possiblyUpdated in self._v_updateSet:
				updated = possiblyUpdated[0] if isinstance(possiblyUpdated,tuple) else possiblyUpdated
				# TODO: If one of the components of the object changed,
				# but the object itself didn't, then this won't catch it.
				# The object could implement getPersistentState() itself to fix it?
				# Or the updater could explicitly call updateLastMod() to force
				# a change on the object itself.
				updated = updated if datastructures.getPersistentState(updated) == persistent.CHANGED else None
				if updated:
					if hasattr( updated, 'updateLastMod' ):
						updated.updateLastMod( end_time )
					self._postNotification( Change.MODIFIED, possiblyUpdated )
					self.containers[updated.containerId].updateLastMod( end_time )
			del self._v_updateSet
			del self._v_updateDepth
		else:
			logger.debug( "Still batching updates at depth %s" % (self._v_updateDepth) )

	class _Updater(object):
		def __init__( self, user ):
			self.user = user

		def __enter__( self ):
			self.user.beginUpdates()

		def __exit__( self, t, value, traceback ):
			self.user.endUpdates()

	def updates( self ):
		"""
		Returns a context manager that wraps its body in calls
		to begin/endUpdates.
		"""
		return self._Updater( self )

	@classmethod
	def _broadcast_change_to( cls, theChange, **kwargs ):
		"""
		Broadcast the change object to the given username.
		Happens asynchronously. Exists as an class attribute method so that it
		can be temporarily overridden by an instance. See the :class:`_NoChangeBroadcast` class.
		"""
		_get_shared_dataserver().enqueue_change( theChange, **kwargs )
		return True

	class _NoChangeBroadcast(object):
		""" A context manager that disables change broadcasts. """
		def __init__( self, ent ):
			self.ent = ent

		def __enter__( self, *args ):
			self.ent._broadcast_change_to = lambda *args, **kwargs: False

		def __exit__( self, *args ):
			del self.ent._broadcast_change_to

	def _postNotification( self, changeType, objAndOrigSharingTuple ):
		logger.debug( "%s asked to post %s on %s", self, changeType, objAndOrigSharingTuple )
		# FIXME: Clean this up, make this not so implicit,
		# make it go through a central place, make it asnyc, etc.

		# We may be called with a tuple, in the case of modifications,
		# or just the object, in the case of creates/deletes.
		obj = None
		origSharing = None
		if not isinstance( objAndOrigSharingTuple, tuple ):
			obj = objAndOrigSharingTuple
			# If we can't get sharing, then there's no point in trying
			# to do anything--the object could never go anywhere
			try:
				origSharing = obj.getFlattenedSharingTargetNames()
			except AttributeError:
				logger.debug( "Failed to get sharing targets on obj of type %s; no one to target change to", type(obj) )
				return
		else:
			# If we were a tuple, then we definitely have sharing
			obj = objAndOrigSharingTuple[0]
			origSharing = objAndOrigSharingTuple[1]

		# Step one is to announce all data changes globally
		if changeType != Change.CIRCLED:
			change = Change( changeType, obj )
			change.creator = self
			self._broadcast_change_to( change, broadcast=True, username=self.username )

		newSharing = obj.getFlattenedSharingTargetNames()
		seenUsernames = set()
		def sendChangeToUser( username, theChange ):
			""" Sends at most one change to a user, taking
			into account aliases. """
			user = self.get_entity( username )
			if user is None:
				logger.warn( 'Unknown user for changes "%s"', username )
				return
			if user.username in seenUsernames: return
			seenUsernames.add( user.username )
			# Fire the change off to the user using different threads.
			self._broadcast_change_to( theChange, username=user.username )

		if origSharing != newSharing and changeType not in (Change.CREATED,Change.DELETED):
			# OK, the sharing changed and its not a new or dead
			# object. People that it used to be shared with will get a
			# DELETE notice. People that it is now shared with will
			# get a SHARED notice--these people should not later get
			# a MODIFIED notice for this action.
			deleteChange = Change( Change.DELETED, obj )
			deleteChange.creator = self
			for shunnedPerson in origSharing - newSharing:
				sendChangeToUser( shunnedPerson, deleteChange )
			createChange = Change( Change.SHARED, obj )
			createChange.creator = self
			for lovedPerson in newSharing - origSharing:
				sendChangeToUser( lovedPerson, createChange )
				newSharing.remove( lovedPerson ) # Don't send modify

		# Deleted events won't change the sharing, so there's
		# no need to look for a union of old and new to send
		# the delete to.

		# Now broadcast the change to anyone that's left.
		change = Change( changeType, obj )
		change.creator = self
		logger.debug( "Sending %s change to %s", changeType, newSharing )
		for lovedPerson in newSharing:
			sendChangeToUser( lovedPerson, change )

	def _acceptIncomingChange( self, change ):
		super(User,self)._acceptIncomingChange( change )
		self.notificationCount = self.notificationCount + 1
		self._broadcastIncomingChange( change )

	def _broadcastIncomingChange( self, change ):
		"""
		Distribute the incoming change to any connected devices/sessions.
		This is an extension point for layers.
		"""
		#TODO: Move the device support to a layer too.
		apnsCon = _get_shared_dataserver().apns
		if not apnsCon:
			if self.devices:
				logger.warn( "No APNS connection, not broadcasting change" )
			return
		if self.devices:
			# If we have any devices, notify them
			userInfo = None
			if change.containerId:
				# Valid NTIIDs are also valid URLs; this
				# condition is mostly for legacy code (tests)
				if ntiids.is_valid_ntiid_string( change.containerId ):
					userInfo = {'url:': change.containerId }

			payload = apns.APNSPayload( badge=self.notificationCount,
										sound='default',
										# TODO: I18N text for this
										alert=change.creator.preferredDisplayName + ' shared an object',
										userInfo=userInfo )
			for device in self.devices.itervalues():
				if not isinstance( device, Device ): continue
				apnsCon.sendNotification( device.deviceId, payload )





@component.adapter(nti.apns.interfaces.IDeviceFeedbackEvent)
def user_devicefeedback( msg ):
	deviceId = msg.deviceId
	hexDeviceId = deviceId.encode( 'hex' )
	# TODO: Very inefficient
	# Switch this to ZCatalog/repoze.catalog
	if msg.timestamp < 0: return
	datasvr = _get_shared_dataserver()
	logger.debug( 'Searching for device %s', hexDeviceId )
	with datasvr.dbTrans():
		for user in (u for u in datasvr.root['users'].itervalues() if isinstance(u,User)):
			if hexDeviceId in user.devices:
				logger.debug( 'Found device id %s in user %s', hexDeviceId, user )
				del user.devices[hexDeviceId]

