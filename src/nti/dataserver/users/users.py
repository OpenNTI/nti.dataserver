#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__( 'logging' ).getLogger( __name__ )

import os
import six
import sys
import time
import numbers
import warnings
import functools
import collections

import zope.intid
from zope import interface
from zope import component
from zope import annotation
from ZODB.interfaces import IConnection
from zope.deprecation import deprecated
from zope.component.factory import Factory
from zope.cachedescriptors.property import cachedIn
from zope.password.interfaces import IPasswordManager
from zope.location import interfaces as loc_interfaces

from z3c.password import interfaces as pwd_interfaces

from nti.dataserver import dicts
from nti.dataserver import sharing
from nti.dataserver import mimetype
from nti.dataserver import datastructures
from nti.dataserver.users.entity import Entity
from nti.dataserver.activitystream_change import Change
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.externalization.datastructures import ExternalizableDictionaryMixin

from nti.ntiids import ntiids

from nti.zodb import minmax

def _get_shared_dataserver(context=None,default=None):
	if default != None:
		return component.queryUtility(nti_interfaces.IDataserver, context=context, default=default)
	return component.getUtility(nti_interfaces.IDataserver, context=context)

# Starts as none, which matches what _get_shared_dataserver takes as its
# clue to use get instead of query. But set to False or 0 to use
# query during evolutions.
BROADCAST_DEFAULT_DS = None

SharingTarget = sharing.SharingTargetMixin
deprecated( 'SharingTarget', 'Prefer sharing.SharingTargetMixin' )

SharingSource = sharing.SharingSourceMixin
deprecated( 'SharingSource', 'Prefer sharing.SharingSourceMixin' )

DynamicSharingTarget = sharing.DynamicSharingTargetMixin
deprecated( 'DynamicSharingTarget', 'Prefer sharing.DynamicSharingTargetMixin' )

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

	def getPassword( self ):
		"""
		Like the zope pluggableauth principals, we allow getting the raw
		bytes of the password. Obviously these are somewhat valuable, even
		when encoded, so take care with them.
		"""
		return self.__encoded

	# Deliberately has no __eq__ method, passwords cannot
	# be directly compared outside the context of their
	# manager.


def named_entity_ntiid(entity):
	return ntiids.make_ntiid( date=ntiids.DATE,
							  provider=nti_interfaces.SYSTEM_USER_NAME,
							  nttype=entity.NTIID_TYPE,
							  specific=ntiids.escape_provider(entity.username.lower()))


class Principal(sharing.SharingSourceMixin, Entity):  # order matters
	""" A Principal represents a set of credentials that has access to the system.

	.. py:attribute:: username

		 The username.
	.. py:attribute:: password

		A password object. Not comparable, only supports a `checkPassword` operation.
	"""

	# TODO: Continue migrating this towards zope.security.principal, the zope principalfolder
	# concept.
	password_manager_name = 'bcrypt'
	def __init__(self,
				 username=None,
				 password=None,
				 parent=None):

		super(Principal,self).__init__(username,
									   parent=parent)
		if password:
			self.password = password

	def has_password(self):
		return bool(self.password)

	def _get_password(self):
		return self.__dict__.get('password', None)
	def _set_password(self,np):
		# TODO: Names for these?
		component.getUtility( pwd_interfaces.IPasswordUtility ).verify( np )
		# NOTE: The password policy objects do not have an option to forbid
		# all whitespace, so we implement that manually here.
		# TODO: Subclass the policy and implement one that does, install that and migrate
		if np and not np.strip(): # but do allow leading/trailing whitespace
			raise user_interfaces.PasswordCannotConsistOfOnlyWhitespace()
		# NOTE: The password policy objects do not have an option to forbid
		# specific passwords from a list, so we implement that manually here.
		# TODO: Subclass the policy and implement one that does, as per above
		if np and np.strip().upper() in user_interfaces._VERBOTEN_PASSWORDS:
			raise user_interfaces.InsecurePasswordIsForbidden(np)

		self.__dict__['password'] = _Password(np, self.password_manager_name)
		# otherwise, no change
	def _del_password(self):
		del self.__dict__['password']
	password = property(_get_password,_set_password,_del_password)

	NTIID_TYPE = None
	NTIID = cachedIn('_v_ntiid')(named_entity_ntiid)

if os.getenv('DATASERVER_TESTING_PLAIN_TEXT_PWDS') == 'True':
	# For use by nti_run_integration_tests, nti_run_general_purpose_tests;
	# plain text passwords are much faster than bcrpyt, and since
	# the tests use HTTP Basic Auth, this makes a difference
	print( "users.py: WARN: Configuring with plain text passwords", file=sys.stderr )
	Principal.password_manager_name = 'Plain Text'

@interface.implementer(nti_interfaces.ICommunity,
					   loc_interfaces.ISublocations)
class Community(sharing.DynamicSharingTargetMixin,Entity):
	# order of inheritance matters

	mime_type = 'application/vnd.nextthought.community'

	@classmethod
	def create_community( cls, dataserver=None, **kwargs ):
		""" Creates (and returns) and places in the dataserver a new community.
		"""
		return cls.create_entity( dataserver=dataserver, **kwargs )

	get_community = Entity.get_entity

	NTIID_TYPE = ntiids.TYPE_NAMED_ENTITY_COMMUNITY
	NTIID = cachedIn('_v_ntiid')(named_entity_ntiid)

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

	def addFriend( self, friend ):
		return True # For compatibility with a FriendsList

	def updates( self ): # For compatibility with User. TODO: Rethink this
		return _NOOPCM

	def sublocations(self):
		# See User; this may not be right (but we are less annotated so
		# it is probably less of a problem). Forums break if they are only
		# annotations and we don't return them.
		annotations = annotation.interfaces.IAnnotations(self, {})
		for val in annotations.values():
			if getattr( val, '__parent__', None ) is self:
				yield val

@interface.implementer(nti_interfaces.IEntityContainer)
@component.adapter(nti_interfaces.ICommunity)
class CommunityEntityContainer(object):

	def __init__( self, context ):
		self.context = context

	def __contains__( self, entity ):
		try:
			return self.context in entity.dynamic_memberships
		except AttributeError:
			return False

@interface.implementer(nti_interfaces.IUnscopedGlobalCommunity)
class Everyone(Community):
	""" A community that represents the entire world. """
	__external_class_name__ = 'Community'
	# 'everyone@nextthought.com' hash
	_avatarURL = 'http://www.gravatar.com/avatar/bb798c65a45658a80281bd3ba26c4ff8?s=128&d=mm'
	_realname = 'Everyone'
	_alias = 'Public'

	def __init__(self):
		super(Everyone,self).__init__( self._realname )

	def __setstate__(self,state):
		for k in ('_avatarURL', '_realname', 'alias'):
			if k in state:
				del state[k]
		super(Everyone,self).__setstate__( state )

from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import _FriendsListMap # bwc
from nti.dataserver.users.friends_lists import DynamicFriendsList
from nti.dataserver.users.friends_lists import _FriendsListUsernameIterable # bwc

ShareableMixin = sharing.ShareableMixin
deprecated( 'ShareableMixin', 'Prefer sharing.ShareableMixin' )

@functools.total_ordering
@interface.implementer( nti_interfaces.IDevice, nti_interfaces.IZContained )
class Device(datastructures.PersistentCreatedModDateTrackingObject,
			 ExternalizableDictionaryMixin):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
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
		result = super(Device, self).toExternalDictionary()
		return result

	def updateFromExternalObject(self, ext):
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


@interface.implementer( nti_interfaces.IDeviceContainer )
class _DevicesMap(datastructures.AbstractNamedLastModifiedBTreeContainer):
	contained_type = nti_interfaces.IDevice
	container_name = 'Devices'

	__name__ = container_name

	def __setitem__( self, key, value ):
		if not isinstance( value, Device ):
			value = Device( value )
		super(_DevicesMap,self).__setitem__( key, value )


nti_interfaces.IDevice.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
									   Factory( Device,
												interfaces=(nti_interfaces.IDevice,)) )


@interface.implementer( nti_interfaces.ITranscriptContainer )
class _TranscriptsMap(datastructures.AbstractNamedLastModifiedBTreeContainer):
	contained_type = nti_interfaces.ITranscript
	container_name = 'Transcripts'
	__name__ = container_name

@interface.implementer( nti_interfaces.IContainerIterable,
						nti_interfaces.IUser,
						loc_interfaces.ISublocations )
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
	as changed using setPersistentStateChanged().
	"""

	_ds_namespace = 'users'
	mime_type = 'application/vnd.nextthought.user'

	@classmethod
	def get_user( cls, username, dataserver=None, default=None ):
		"""
		Returns the User having ``username``, else None.

		:param basestring username: The username to find. Can also be an instance of
			this class, in which case it is immediately returned (effectively making this
			behave like a :mod:`zope.interface` cast. Note that it is this specific
			class, not :class:`User` in general.
		"""
		if isinstance( username, cls ):
			return username
		result = cls.get_entity( username, dataserver=dataserver, default=default ) if username else None
		return result if isinstance( result, User ) else default # but this instance check is the base class

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

	# The last login time is an number of seconds (as with time.time).
	# When it gets reset, the number of outstanding notifications also
	# resets. It is writable, number is not...
	lastLoginTime = minmax.NumericPropertyDefaultingToZero(b'lastLoginTime', minmax.NumericMaximum, as_number=True)
	# ...although, pending a more sophisticated notification tracking
	# mechanism, we are allowing notification count to be set
	notificationCount = minmax.NumericPropertyDefaultingToZero( b'notificationCount', minmax.MergingCounter )

	# TODO: If no AvatarURL is set when externalizing,
	# send back a gravatar URL for the primary email:
	# http://www.gravatar.com/avatar/%<Lowercase hex MD5>=44&d=mm

	def __init__(self, username, password=None,

				 parent=None, _stack_adjust=0):
		super(User,self).__init__(username, password=password,
								  parent=parent)
		nti_interfaces.IUser['username'].bind(self).validate( self.username )
		# We maintain a Map of our friends lists, organized by
		# username (only one friend with a username)

		if self.__parent__ is None and component.queryUtility( zope.intid.IIntIds ) is not None:
			warnings.warn( "No parent provided. User will have no Everyone list or Community; either use User.create_user or provide parent kwarg",
						   stacklevel=(2 if type(self) == User else 3) + _stack_adjust )

		self.friendsLists = _FriendsListMap()
		self.friendsLists.__parent__ = self

		# Join our default community
		if self.__parent__:
			everyone = self.__parent__.get( Everyone._realname )
			if everyone:
				self.record_dynamic_membership( everyone )

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

	def __setstate__(self, data):
		# Old objects might have a 'stream' of none? For no particular
		# reason?
		if isinstance(data, collections.Mapping) and 'stream' in data and data['stream'] is None:
			del data['stream']

		super(User, self).__setstate__(data)

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

	NTIID_TYPE = ntiids.TYPE_NAMED_ENTITY_USER

	def update_last_login_time(self):
		self.lastLoginTime = time.time()

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		#with self._NoChangeBroadcast( self ):
		super(User,self).updateFromExternalObject( parsed, *args, **kwargs )
		updated = None
		lastLoginTime = parsed.pop( 'lastLoginTime', None )
		if isinstance( lastLoginTime, numbers.Number ) and self.lastLoginTime < lastLoginTime:
			self.lastLoginTime = lastLoginTime
			self.notificationCount = 0 # reset to zero. Note that we don't del the property to keep the same persistent object object
			updated = True

		notificationCount = parsed.pop( 'NotificationCount', None )
		if isinstance( notificationCount, numbers.Number ):
			self.notificationCount = notificationCount
			updated = True

		if 'password' in parsed:
			old_pw = None
			if self.has_password():
				# To change an existing password, you must send the old
				# password (The default, empty string, is never a valid password and lets
				# us produce better error messages then having no default)
				old_pw = parsed.pop( 'old_password', '' )
				# And it must match
				if not self.password.checkPassword( old_pw ):
					raise user_interfaces.OldPasswordDoesNotMatchCurrentPassword()
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


		# See notes on how ignoring and accepting values may arrive.
		# NOTE2: In the past, we avoided broadcasting CIRCLED notices during this
		# process; is that necessary?
		def handle_ext( resetAll, reset, add, remove, value ):
			if isinstance( value, collections.Sequence ):
				updated = True # TODO: Py3 nonlocal keyword.
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

	def _get_dynamic_sharing_targets_for_read( self ):
		"""
		Overrides the super method to return both the communities we are a
		member of, plus the friends lists we ourselves have created that are dynamic.
		"""
		result = self.xxx_hack_filter_non_memberships( super(User,self)._get_dynamic_sharing_targets_for_read(),
													   "Relationship trouble: User %s is no longer a member of %s. Ignoring for dynamic read" )

		for fl in self.friendsLists.values():
			if nti_interfaces.IDynamicSharingTarget.providedBy( fl ):
				result.add( fl )
		return result

	def _get_entities_followed_for_read( self ):
		return self.xxx_hack_filter_non_memberships( super(User,self)._get_entities_followed_for_read(),
													 "Relationship trouble: User %s is no longer a member of %s. Ignoring for followed read" )


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
			# Bypass the whole mess of broadcasting and going through the DS and change listeners,
			# and just notice the incoming change.
			# TODO: Clean this up, go back to event based.
			self._noticeChange( change )
			return change # which is both True and useful

	def is_accepting_shared_data_from( self, source ):
		""" We say we're accepting so long as we're not ignoring. """
		# TODO: the 'incoming' group discussed in super will obsolete this
		return not self.is_ignoring_shared_data_from( source )

	def getFriendsList( self, name ):
		""" Returns the friends list having the given name, otherwise
		returns None. """
		return self.friendsLists.get( name )

	def getFriendsLists( self, name=None ):
		""" Returns all the friends lists"""
		return tuple(self.friendsLists.values())

	def maybeCreateContainedObjectWithType( self, datatype, externalValue ):
		if datatype in ( self.devices.container_name, Device.mimeType ):
			result = Device(externalValue)
		else:
			# FIXME: This is a hack to translate mimetypes to the old
			# style of name that works with self.containers
			if datatype == FriendsList.mimeType:
				datatype = self.friendsLists.container_name
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


	def deleteContainedObject( self, containerId, containedId ):
		try:
			self.containers._p_activate()
			self.containers._p_jar.readCurrent( self.containers )
		except AttributeError:
			pass
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

	def getContainer( self, containerId, defaultValue=None, context_cache=None ):
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

		.. todo:: See comments in this method; annotations no longer supported.

		Note that this is used during the processing of :class:`zope.lifecycleevent.IObjectMovedEvent`,
		when :func:`zope.container.contained.dispatchToSublocations` comes through
		and recursively lets all the children know about the event. Also note that :class:`zope.lifecycleevent.IObjectRemovedEvent`
		is a kind of `IObjectMovedEvent`, so when the user is deleted, events are fired for all
		of his contained objects as well, allowing things like intid cleanup to work.
		"""

		yield self.containers
		# Now anything else in containers that we put there that is actually
		# a child of us (this includes self.friendsLists and self.devices)
		for v in self.containers.itervalues():
			if getattr( v, '__parent__', None ) is self:
				yield v

		# If we have annotations, then if the annotated value thinks of
		# us as a parent, we need to return that. See zope.annotation.factory
		#### XXX FIXME:
		#### This is wrong (and so commented out). Specifically, for ObjectAddedEvent,
		#### any annotations we have already established get their own intids,
		#### even if they are not meant to be addressable like that, potentially
		#### keeping them alive for too long. This also means that annotations get
		#### indexed, which is probably also not what we want. It causes issues for
		#### IUserProfile annotation in particular.
		#### TODO: But what does turning this off break? Certain migration patterns?
		#### Or does it break deleting a user? Chat message storage winds up with
		#### too many objects still with intids?
		#annotations = zope.annotation.interfaces.IAnnotations(self, {})

		# Technically, IAnnotations doesn't have to be iterable of values,
		# but it always is (see zope.annotation.attribute)
		#for val in annotations.values():
		#	if getattr( val, '__parent__', None ) is self:
		#		yield val

	def _is_container_ntiid( self, containerId ):
		"""
		Filters out things that are not used as NTIIDs. In the future,
		this will be easy (as soon as everything is tag-based). Until then,
		we rely on the fact that all our custom keys are upper cased.
		"""
		return len(containerId) > 1 and \
			   (containerId.startswith( 'tag:nextthought.com' )
				or containerId[0].islower())

	def iterntiids( self, include_stream=True, stream_only=False ):
		"""
		Returns an iterable across the NTIIDs that are relevant to this user.
		"""
		# Takes into account our things, things shared directly to us,
		# and things found in dynamic things we care about, which includes
		# our memberships and things we own
		seen = set()
		if not stream_only:
			for k in self.containers:
				if self._is_container_ntiid(k) and k not in seen:
					seen.add( k )
					yield k

			for k in self.containersOfShared:
				if self._is_container_ntiid(k) and k not in seen:
					seen.add( k )
					yield k
		if include_stream:
			for k in self.streamCache:
				if self._is_container_ntiid(k) and k not in seen:
					seen.add( k )
					yield k

		interesting_dynamic_things = set(self.dynamic_memberships) | {x for x in self.friendsLists.values() if nti_interfaces.IDynamicSharingTarget.providedBy(x)}
		for com in interesting_dynamic_things:
			if not stream_only and hasattr( com, 'containersOfShared' ):
				for k in com.containersOfShared:
					if self._is_container_ntiid( k ) and k not in seen:
						seen.add( k )
						yield k
			if include_stream and hasattr( com, 'streamCache' ):
				for k in com.streamCache:
					if self._is_container_ntiid( k ) and k not in seen:
						seen.add( k )
						yield k


	def itercontainers( self ):
		# TODO: Not sure about this. Who should be responsible for
		# the UGD containers? Should we have some different layout
		# for that (probably).
		return (v
				for v in self.containers.containers.itervalues()
				if nti_interfaces.INamedContainer.providedBy( v ) )


	#@deprecate("No replacement; not needed") # noisy if enabled; logic in flagging_views still needs its existence until rewritten
	def updates( self ):
		"""
		This is officially deprecated now.
		"""
		return _NOOPCM

	def _acceptIncomingChange( self, change, direct=True ):
		accepted = super(User,self)._acceptIncomingChange( change, direct=direct )
		if accepted:
			self.notificationCount.increment()
			self._broadcastIncomingChange( change )

	def _broadcastIncomingChange( self, change ):
		"""
		Distribute the incoming change to any connected devices/sessions.
		This is an extension point for layers.
		"""
		#TODO: Move this out to a listener somewhere
		apnsCon = _get_shared_dataserver().apns
		if not apnsCon:
			if self.devices:
				logger.warn( "No APNS connection, not broadcasting change" )
			return
		if self.devices:
			from nti.apns.payload import APNSPayload
			# If we have any devices, notify them
			userInfo = None
			if change.containerId:
				# Valid NTIIDs are also valid URLs; this
				# condition is mostly for legacy code (tests)
				if ntiids.is_valid_ntiid_string( change.containerId ):
					userInfo = {'url:': change.containerId }

			payload = APNSPayload( badge=self.notificationCount.value,
								   sound='default',
								   # TODO: I18N text for this
								   alert='An object was shared with you', #change.creator.preferredDisplayName + ' shared an object',
								   userInfo=userInfo )
			for device in self.devices.itervalues():
				if not isinstance( device, Device ):
					continue
				__traceback_info__ = device, payload, change
				try:
					apnsCon.sendNotification( device.deviceId, payload )
				except Exception: # Big catch: this is not crucial, we shouldn't hurt anything without it
					logger.exception("Failed to send APNS notification" )

	def xxx_hack_filter_non_memberships(self, relationships, log_msg=None, the_logger=logger):
		"""
		XXX Temporary hack: Filter out some non-members that crept in. There
		should be no more new ones after this date, but leave this code here as a warning
		for awhile in case any do creep in.

		:return: set of memberships
		"""
		result = set(relationships)
		discarded = []
		for x in list(result):
			if nti_interfaces.IFriendsList.providedBy( x ) and self not in x:
				discarded.append( (x,x.NTIID) )
				result.discard( x )

		if discarded and log_msg and the_logger is not None:
			the_logger.warning( log_msg, self, discarded )

		return result


# We have a few subclasses of User that store some specific
# information and directly implement some interfaces.
# Right now, we're not exposing this information directly to clients,
# so this is an implementation detail. Thus we make their class names
# be 'User' as well.
# TODO: MimeTypes?

@interface.implementer( nti_interfaces.IOpenIdUser )
class OpenIdUser(User):
	__external_class_name__ = 'User'

	identity_url = None

	def __init__(self, username, **kwargs ):
		id_url = kwargs.pop( 'identity_url', None)
		super(OpenIdUser,self).__init__(username,**kwargs)
		if id_url:
			self.identity_url = id_url

@interface.implementer( nti_interfaces.IFacebookUser )
class FacebookUser(User):
	__external_class_name__ = 'User'
	facebook_url = None

	def __init__(self, username, **kwargs ):
		id_url = kwargs.pop( 'facebook_url', None)
		super(FacebookUser,self).__init__(username,**kwargs)
		if id_url:
			self.facebook_url = id_url

class _NoOpCm(object):
	def __enter__( self ):
		pass

	def __exit__( self, t, v, tb ):
		pass
_NOOPCM = _NoOpCm()

from nti.apns import interfaces as apns_interfaces
@component.adapter(apns_interfaces.IDeviceFeedbackEvent)
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
	# NOTE: We are not using a site policy here so the listener is limited
	if IConnection( component.getSiteManager(), None ):
		feedback()
	else:
		component.getUtility( IDataserverTransactionRunner )( feedback )


def onChange( datasvr, msg, target=None, broadcast=None, **kwargs ):
	"""

	:param broadcast: If true, then we ignore this event. See chat_transcripts.py.
	"""
	if target and not broadcast:
		#logger.debug( 'Incoming change to %s', target )
		entity = target
		try:
			entity._p_activate()
			entity._p_jar.readCurrent( entity )
		except AttributeError:
			pass

		entity._noticeChange( msg )
