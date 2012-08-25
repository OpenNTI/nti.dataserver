#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import


logger = __import__( 'logging' ).getLogger( __name__ )

import warnings
import numbers
import functools
import time
import six
import collections

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.keyreference.interfaces import IKeyReference

from zope.component.factory import Factory
from zope.deprecation import deprecated

import zope.intid

from z3c.password import interfaces as pwd_interfaces

import persistent


from nti.ntiids import ntiids
from nti.zodb import minmax

from nti.externalization.persistence import  getPersistentState, setPersistentStateChanged
from nti.externalization.datastructures import ExternalizableDictionaryMixin
import nti.externalization.internalization


from nti.dataserver import datastructures
from nti.dataserver import dicts
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import mimetype
from nti.dataserver import sharing
from nti.dataserver.activitystream_change import Change
from nti import apns

import nti.apns.interfaces

from ZODB.interfaces import IConnection
from nti.dataserver.interfaces import IDataserverTransactionRunner


def _get_shared_dataserver(context=None,default=None):
	if default != None:
		return component.queryUtility( nti_interfaces.IDataserver, context=context, default=default )
	return component.getUtility( nti_interfaces.IDataserver, context=context )


from .entity import Entity

SharingTarget = sharing.SharingTargetMixin
deprecated( 'SharingTarget', 'Prefer sharing.SharingTargetMixin' )

SharingSource = sharing.SharingSourceMixin
deprecated( 'SharingSource', 'Prefer sharing.SharingSourceMixin' )

DynamicSharingTarget = sharing.DynamicSharingTargetMixin
deprecated( 'DynamicSharingTarget', 'Prefer sharing.DynamicSharingTargetMixin' )

from zope.password.interfaces import IPasswordManager

class _Password(object):
	"""
	Represents the password of a principal, as
	encoded by a password manager. Immutable.
	"""

	def __init__( self, password, manager_name='bcrypt' ):
		"""
		Creates a password given the plain text and the name of a manager
		to encode it with.

		:key manager_name string: The name of the :class:`IPasswordManager` to use
			to manager this password. The default is ``bcrypt,`` which uses a secure,
			salted hash. This is the recommended manager. If it is not available (due to the
			absence of C extensions?) the ``pbkdf2`` manager can be used. See :mod:`z3c.bcrypt`
			and :mod:`zope.password`.
		"""

		self.__encoded = component.getUtility( IPasswordManager, name=manager_name ).encodePassword( password )
		self.password_manager = manager_name

	def checkPassword( self, password ):
		"""
		:return: Whether the given (plain text) password matches the
		encoded password stored by this object.
		"""
		return component.getUtility( IPasswordManager, name=self.password_manager ).checkPassword( self.__encoded, password )

	# Deliberately has no __eq__ method, passwords cannot
	# be compared


class Principal(Entity,sharing.SharingSourceMixin):
	""" A Principal represents a set of credentials that has access to the system.

	.. py:attribute:: username

		 The username.
	.. py:attribute:: password

		A password object. Not comparable, only supports a `checkPassword` operation.
	"""

	# TODO: Continue migrating this towards zope.security.principal, the zope principalfolder
	# concept.
	def __init__(self,
				 username=None,
				 password=None,
				 parent=None):

		super(Principal,self).__init__(username,
									   parent=parent)
#		if not username or '@' not in username:
#			raise ValueError( 'Illegal username ' + username )

		if password:
			self.password = password

	def has_password(self):
		return bool(self.password)

	def _get_password(self):
		return self.__dict__.get('password', None)
	def _set_password(self,np):
		# TODO: Names for these
		component.getUtility( pwd_interfaces.IPasswordUtility ).verify( np )
		self.__dict__['password'] = _Password(np)
		# otherwise, no change
	password = property(_get_password,_set_password)


class Community(Entity,sharing.DynamicSharingTargetMixin):

	@classmethod
	def create_community( cls, dataserver=None, **kwargs ):
		""" Creates (and returns) and places in the dataserver a new community.
		"""
		return cls.create_entity( dataserver=dataserver, **kwargs )


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
	# 'everyone@nextthought.com' hash
	_avatarURL = 'http://www.gravatar.com/avatar/bb798c65a45658a80281bd3ba26c4ff8?s=128&d=mm'
	_realname = 'Everyone'
	_alias = 'Public'
	def __init__(self):
		super(Everyone,self).__init__( 'Everyone' )

	def __setstate__(self,state):
		for k in ('_avatarURL', '_realname', 'alias'):
			if k in state:
				del state[k]
		super(Everyone,self).__setstate__( state )

from .friends_lists import FriendsList
from .friends_lists import DynamicFriendsList
from .friends_lists import _FriendsListUsernameIterable # bwc
from .friends_lists import _FriendsListMap # bwc

ShareableMixin = sharing.ShareableMixin
deprecated( 'ShareableMixin', 'Prefer sharing.ShareableMixin' )


@functools.total_ordering
class Device(persistent.Persistent,
			 datastructures.CreatedModDateTrackingObject,
			 ExternalizableDictionaryMixin):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements( nti_interfaces.IDevice, nti_interfaces.IZContained )
	__external_can_create__ = True

	__name__ = None
	__parent__ = None

	def __init__(self, deviceId):
		"""
		:param deviceId: Either a basic dictionary containing `StandardExternalFields.ID`
			or a string in hex encoding the bytes of a device id.
		"""
		super(Device,self).__init__()
		if isinstance(deviceId,collections.Mapping):
			deviceId = deviceId[datastructures.StandardExternalFields.ID]
		# device id arrives in hex encoding
		self.deviceId = deviceId.decode( 'hex' )

	def get_containerId( self ):
		return _DevicesMap.container_name
	def set_containerId( self, cid ):
		pass
	containerId = property( get_containerId, set_containerId )

	@property
	def id(self):
		# Make ID not be writable
		return self.deviceId.encode('hex')

	def toExternalObject(self):
		result = super(Device,self).toExternalDictionary()
		return result

	def updateFromExternalObject(self,ext):
		pass

	def __eq__(self, other):
		try:
			return self.deviceId == other.deviceId
		except AttributeError:
			return NotImplemented

	def __lt__(self, other):
		try:
			return self.deviceId < other.deviceId
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return self.deviceId.__hash__()



class _DevicesMap(datastructures.AbstractNamedLastModifiedBTreeContainer):
	interface.implements(nti_interfaces.IDeviceContainer)
	contained_type = nti_interfaces.IDevice
	container_name = 'Devices'

	def __setitem__( self, key, value ):
		if not isinstance( value, Device ):
			value = Device( value )
		super(_DevicesMap,self).__setitem__( key, value )


nti_interfaces.IDevice.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
									   Factory( Device,
												interfaces=(nti_interfaces.IDevice,)) )


class _TranscriptsMap(datastructures.AbstractNamedLastModifiedBTreeContainer):
	interface.implements(nti_interfaces.ITranscriptContainer)
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
						 nti_interfaces.IUser,
						 loc_interfaces.ISublocations)

	_ds_namespace = 'users'
	mime_type = 'application/vnd.nextthought.user'

	@classmethod
	def get_user( cls, username, dataserver=None, default=None ):
		""" Returns the User having `username`, else None. """
		result = cls.get_entity( username, dataserver=dataserver, default=default ) if username else None
		return result if isinstance( result, User ) else default

	@classmethod
	def create_user( cls, dataserver=None, **kwargs ):
		"""
		Creates (and returns) and places in the dataserver a new user,
		constructed using the keyword arguments given, the same as
		those the User constructor takes. Raises a :class:`KeyError`
		if the user already exists. You handle the transaction.
		"""
		return cls.create_entity( dataserver=dataserver, **kwargs )

	delete_user = Principal.delete_entity

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


	# TODO: If no AvatarURL is set when externalizing,
	# send back a gravatar URL for the primary email:
	# http://www.gravatar.com/avatar/%<Lowercase hex MD5>=44&d=mm

	def __init__(self, username, password=None,

				 parent=None, _stack_adjust=0):
		super(User,self).__init__(username, password=password,
								  parent=parent)
		# We maintain a Map of our friends lists, organized by
		# username (only one friend with a username)
		_create_fl = True

		if self.__parent__ is None and component.queryUtility( zope.intid.IIntIds ) is not None:
			warnings.warn( "No parent provided. User will have no Everyone list; either use User.create_user or provide parent kwarg",
						   stacklevel=(2 if type(self) == User else 3) + _stack_adjust )
			_create_fl = False


		self.friendsLists = _FriendsListMap()
		self.friendsLists.__parent__ = self

		# Join our default community
		self._communities.add( 'Everyone' )

		# We maintain a list of devices associated with this user
		# TODO: Want a persistent set?
		self.devices = _DevicesMap()
		self.devices.__parent__ = self

		# Create the containers, along with the initial set of contents.
		# Note that this doesn't reparent them, they stay parented by us
		self.containers = datastructures.ContainedStorage(create=self,
														  containersType=dicts.CaseInsensitiveLastModifiedDict,
														  containers={self.friendsLists.container_name: self.friendsLists,
																	  self.devices.container_name: self.devices })
		self.containers.__parent__ = self
		self.containers.__name__ = '' # TODO: This is almost certainly wrong. We hack around it
		self.__install_container_hooks()

		# The last login time is an number of seconds (as with time.time).
		# When it gets reset, the number of outstanding notifications also
		# resets. It is writable, number is not...
		self.lastLoginTime = minmax.Maximum(0)
		# ...although, pending a more sophisticated notification tracking
		# mechanism, we are allowing notification count to be set
		self.notificationCount = minmax.MergingCounter(0)

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
		self.containers.afterGetContainedObject = self._trackObjectUpdates
		# Deleting is handled with events.
		# TODO: Make the rest use events as well

	def __setstate__( self, state ):
		super(User,self).__setstate__( state )
		# re-install our hooks that are transient
		self.__install_container_hooks()

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

	def update_last_login_time(self):
		self.lastLoginTime.value = time.time()

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		with self._NoChangeBroadcast( self ):
			super(User,self).updateFromExternalObject( parsed, *args, **kwargs )
			updated = None
			lastLoginTime = parsed.pop( 'lastLoginTime', None )
			if isinstance( lastLoginTime, numbers.Number ) and self.lastLoginTime.value < lastLoginTime:
				self.lastLoginTime.value = lastLoginTime
				self.notificationCount.value = 0
				updated = True

			notificationCount = parsed.pop( 'NotificationCount', None )
			if isinstance( notificationCount, numbers.Number ):
				self.notificationCount.value = notificationCount
				updated = True

			if 'password' in parsed:
				old_pw = None
				if self.has_password():
					# To change an existing password, you must send the old
					# password
					old_pw = parsed.pop( 'old_password')
					# And it must match
					if not self.password.checkPassword( old_pw ):
						raise ValueError( "Old password does not match" )
				password = parsed.pop( 'password' )
				# TODO: Names/sites for these? That are distinct from the containment structure?
				component.getUtility( pwd_interfaces.IPasswordUtility ).verify( password, old_pw )
				self.password = password # NOTE: This re-verifies
				updated = True

			# Muting/Unmuting conversations. Notice that we only allow
			# a single thing to be changed at once. Also notice that we never provide
			# the full list of currently muted objects as external data. These
			# both support the idea that the use-case for this feature is a single button
			# in the UI at the conversation level, and that 'unmuting' a conversation is
			# only available /immediately/ after muting it, as an 'Undo' action (like in
			# gmail). Our muted conversations still show up in search results, as in gmail.
			if 'mute_conversation' in parsed:
				self.mute_conversation( parsed.pop( 'mute_conversation' ) )
				updated = True
			elif 'unmute_conversation' in parsed:
				self.unmute_conversation( parsed.pop( 'unmute_conversation' ) )
				updated = True

			# These two arrays cancel each other out. In order to just have to
			# deal with sending one array or the other, the presence of an entry
			# in one array will remove it from the other. This happens

			# See notes on how ignoring and accepting values may arrive
			def handle_ext( resetAll, reset, add, remove, value ):
				if isinstance( value, collections.Sequence ):
					updated = True
					# replacement list
					resetAll()
					for x in value:
						reset( x )
						add( x )
				elif isinstance( value, collections.Mapping ):
					updated = True
					# adds and removes
					# Could be present but None, so be explicit about default
					for x in (value.get( 'add' ) or ()):
						reset( x )
						add( x )
					for x in (value.get( 'remove') or () ):
						remove( x )
				elif value is not None:
					updated = True
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
			return updated

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
			self._broadcast_change_to( change, target=self )
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
		# TODO: This should not be needed anymore as
		# intid listeners, etc, adapt to IKeyReference which adapts to IConnection
		# which walks the containment tree
		if getattr( contained, '_p_jar', self ) is None \
			and getattr( self, '_p_jar' ) is not None:
			self._p_jar.add( contained )

		result = self.containers.addContainedObject( contained )
		return result

	def _postCreateNotification( self, obj ):
		intids = component.queryUtility( zope.intid.IIntIds )
		__traceback_info__ = obj, intids
		try:
			assert intids is None or intids.getId( obj ) is not None, "Should have int id for obj"
		except KeyError:
			IKeyReference( obj ) # No intid. Why? Can we not adapt to IKeyRef?
			raise # If we could adapt to key ref, raise the original missing
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
		if self._p_jar and self.containers._p_jar:
			self._p_jar.readCurrent( self.containers )
		return self.containers.deleteContainedObject( containerId, containedId )

	# TODO: Could/Should we use proxy objects to automate
	# the update process? Allowing updates directly to deep objects?
	# What about monitoring the resources associated with the transaction
	# and if any of them belong to us posting a notification? (That seems
	# convenient but a poor separation of concerns)

	def getContainedObject( self, containerId, containedId, defaultValue=None ):
		if containerId == self.containerId: # "Users"
			return self
		return self.containers.getContainedObject( containerId, containedId, defaultValue )

	def getContainer( self, containerId, defaultValue=None ):
		stored_value = self.containers.getContainer( containerId, defaultValue )
		return stored_value


	def getAllContainers( self ):
		""" Returns all containers, as a map from containerId to container.
		The returned value *MUST NOT* be modified."""
		return self.containers.containers

	def values(self, of_type=None):
		"""
		Returns something that iterates across all contained (owned) objects of this user.
		This is intended for use during migrations (enabling :func:`zope.generations.utility.findObjectsProviding`)
		and not general use.

		:param type of_type: If given, then only values that are instances of the given type
			will be returned.
		:type of_type: A class or interface.
		"""
		# We could simply return getAllContainers().values() and let findObjectsProviding
		# deal with the traversal, but this way is a tad more general
		if interface.interfaces.IInterface.providedBy( of_type ):
			test = of_type.providedBy
		elif isinstance(of_type, six.class_types):
			test = lambda x: isinstance( x, of_type )
		else:
			test = lambda x: True

		for container in self.getAllContainers().values():
			if not hasattr( container, 'values' ): continue
			for o in container.values():
				if test(o):
					yield o

		# TODO: This should probably be returning the annotations, too, just like
		# sublocations does, yes?

	def sublocations(self):
		"""
		The sublocations of a user are his FriendsLists, his Devices,
		all the contained things he has created, and anything annotated
		on him that was in ILocation (see :mod:`zope.annotation.factory`).

		Note that this is used during the processing of :class:`zope.lifecycleevent.IObjectMovedEvent`,
		when :func:`zope.container.contained.dispatchToSublocations` comes through
		and recursively lets all the children know about the event. Also note that :class:`zope.lifecycleevent.IObjectRemovedEvent`
		is a kind of `IObjectMovedEvent`, so when the user is deleted, events are fired for all
		of his contained objects as well, allowing things like intid cleanup to work.
		"""

		yield self.friendsLists
		yield self.devices
		yield self.containers
		# If we have annotations, then if the annotated value thinks of
		# us as a parent, we need to return that. See zope.annotation.factory
		annotations = zope.annotation.interfaces.IAnnotations(self, {})

		# Technically, IAnnotations doesn't have to be iterable of values,
		# but it always is (see zope.annotation.attribute)
		for val in annotations.values():
			if getattr( val, '__parent__', None ) is self:
				yield val

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
		# TODO: This could be much more efficient: iter( {k for k in itertools.chain( owned, shared )} )?
		owned = [k for k in self.containers if self._is_container_ntiid( k )]
		shared = [k for k in self.containersOfShared if self._is_container_ntiid( k )]
		return iter( set( owned ) | set( shared ) )

	def itercontainers( self ):
		# TODO: Not sure about this. Who should be responsible for
		# the UGD containers? Should we have some different layout
		# for that (probably).
		return (v
				for v in self.containers.containers.itervalues()
				if nti_interfaces.INamedContainer.providedBy( v ) )

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
			self._v_updateSet.append( (obj,obj.sharingTargets)
									  if isinstance( obj, ShareableMixin)
									  else obj )

	def didUpdateObject( self, *objs ):
		if getattr(self, '_v_updateDepth', 0) > 0:
			for obj in objs:
				setPersistentStateChanged( obj )
				self._trackObjectUpdates( obj )

	def endUpdates(self):
		""" Commits any outstanding transaction and posts notifications
		referring to the updated objects. """
		if not hasattr(self, '_v_updateSet') or not hasattr(self,'_v_updateDepth'):
			raise Exception( 'Update depth inconsistent' )

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
				updated = updated if getPersistentState(updated) == persistent.CHANGED else None
				if updated:
					# updating last mod should be handled by ObjectModifiedEvents now
					#if hasattr( updated, 'updateLastMod' ):
					#	updated.updateLastMod( end_time )
					self._postNotification( Change.MODIFIED, possiblyUpdated )
					self.containers[updated.containerId].updateLastMod( end_time )
			del self._v_updateSet
			del self._v_updateDepth
		else:
			__traceback_info__ = self._v_updateDepth, self._v_updateSet
			raise Exception( "Nesting not allowed" )
			#logger.debug( "Still batching updates at depth %s" % (self._v_updateDepth) )

	class _Updater(object):
		def __init__( self, user ):
			self.user = user

		def __enter__( self ):
			self.user.beginUpdates()

		def __exit__( self, t, value, traceback ):
			if t is None:
				# Only do this if we're not in the process of throwing
				# an exception, as it might raise again
				self.user.endUpdates()
			else:
				# However, we must be sure that the update depth
				# regains consistency
				# FIXME: This is jacked up.
				if hasattr( self.user, '_v_updateSet' ):
					del self.user._v_updateSet
				if hasattr( self.user, '_v_updateDepth' ):
					del self.user._v_updateDepth

	def updates( self ):
		"""
		Returns a context manager that wraps its body in calls
		to begin/endUpdates.
		"""
		return self._Updater( self )

	@classmethod
	def _broadcast_change_to( cls, theChange, target=None, broadcast=None ):
		"""
		Broadcast the change object to the given username.
		Happens asynchronously. Exists as an class attribute method so that it
		can be temporarily overridden by an instance. See the :class:`_NoChangeBroadcast` class.
		"""
		kwargs = {'target': target}
		if broadcast is not None:
			kwargs['broadcast'] = broadcast
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
		logger.debug( "%s asked to post %s", self, changeType )
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
				origSharing = obj.sharingTargets
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
			self._broadcast_change_to( change, broadcast=True, target=self )

		newSharing = obj.sharingTargets
		seenTargets = set()
		def sendChangeToUser( user, theChange ):
			""" Sends at most one change to a user, taking
			into account aliases. """

			if user in seenTargets or user is None:
				return
			seenTargets.add( user )
			# Fire the change off to the user using different threads.
			self._broadcast_change_to( theChange, target=user )

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
		accepted = super(User,self)._acceptIncomingChange( change )
		if accepted:
			self.notificationCount.value = self.notificationCount.value + 1
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

			payload = apns.APNSPayload( badge=self.notificationCount.value,
										sound='default',
										# TODO: I18N text for this
										alert='An object was shared with you', #change.creator.preferredDisplayName + ' shared an object',
										userInfo=userInfo )
			for device in self.devices.itervalues():
				if not isinstance( device, Device ): continue
				apnsCon.sendNotification( device.deviceId, payload )

# We have a few subclasses of User that store some specific
# information and directly implement some interfaces.
# Right now, we're not exposing this information directly to clients,
# so this is an implementation detail. Thus we make their class names
# be 'User' as well.
# TODO: MimeTypes?

class OpenIdUser(User):
	__external_class_name__ = 'User'
	interface.implements( nti_interfaces.IOpenIdUser )
	identity_url = None

	def __init__(self, username, **kwargs ):
		id_url = kwargs.pop( 'identity_url', None)
		super(OpenIdUser,self).__init__(username,**kwargs)
		if id_url:
			self.identity_url = id_url


class FacebookUser(User):
	__external_class_name__ = 'User'

	interface.implements( nti_interfaces.IFacebookUser )
	facebook_url = None


	def __init__(self, username, **kwargs ):
		id_url = kwargs.pop( 'facebook_url', None)
		super(FacebookUser,self).__init__(username,**kwargs)
		if id_url:
			self.facebook_url = id_url

@component.adapter(nti_interfaces.IContained, zope.intid.interfaces.IIntIdRemovedEvent)
def user_willRemoveIntIdForContainedObject( contained, event ):

	# Make the containing owner broadcast the DELETED event /now/,
	# while we can still get an ID, to keep catalogs and whatnot
	# up-to-date.
	if hasattr( contained.creator, '_postDeleteNotification' ):
		contained.creator._postDeleteNotification( contained )

@component.adapter(nti.apns.interfaces.IDeviceFeedbackEvent)
def user_devicefeedback( msg ):
	def feedback():
		deviceId = msg.deviceId
		hexDeviceId = deviceId.encode( 'hex' )
		# TODO: Very inefficient
		# Switch this to ZCatalog/repoze.catalog
		if msg.timestamp < 0: return
		datasvr = _get_shared_dataserver()
		logger.debug( 'Searching for device %s', hexDeviceId )
		for user in (u for u in datasvr.root['users'].itervalues() if isinstance(u,User)):
			if hexDeviceId in user.devices:
				logger.debug( 'Found device id %s in user %s', hexDeviceId, user )
				del user.devices[hexDeviceId]

	# Be sure we run in the right site and transaction.
	# Our usual caller is in nti.apns and knows nothing about that.
	if IConnection( component.getSiteManager(), None ):
		feedback()
	else:
		component.getUtility( IDataserverTransactionRunner )( feedback )


def onChange( datasvr, msg, target=None, broadcast=None, **kwargs ):
	if target and not broadcast:
		logger.debug( 'Incoming change to %s', target )
		entity = target
		if getattr( entity, '_p_jar', None):
			getattr( entity, '_p_jar' ).readCurrent( entity )
		entity._noticeChange( msg )
