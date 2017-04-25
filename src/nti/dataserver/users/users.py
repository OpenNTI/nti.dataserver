#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
import sys
import time
import BTrees
import numbers
import warnings
import collections

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import cachedIn

from zope.deprecation import deprecated

from zope.intid.interfaces import IIntIds

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from zope.location.interfaces import ISublocations

from zope.password.interfaces import IPasswordManager

from ZODB.interfaces import IConnection

from z3c.password import interfaces as pwd_interfaces

from persistent.list import PersistentList

from persistent.mapping import PersistentMapping

from persistent.persistence import Persistent

from nti.apns import interfaces as apns_interfaces

from nti.dataserver import dicts
from nti.dataserver import sharing

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IOpenIdUser
from nti.dataserver.interfaces import ITranscript
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import IFacebookUser
from nti.dataserver.interfaces import IIntIdIterable
from nti.dataserver.interfaces import INamedContainer
from nti.dataserver.interfaces import IContainerIterable
from nti.dataserver.interfaces import ITranscriptContainer
from nti.dataserver.interfaces import IDynamicSharingTarget
from nti.dataserver.interfaces import IUserBlacklistedStorage
from nti.dataserver.interfaces import IUserDigestEmailMetadata
from nti.dataserver.interfaces import ITargetedStreamChangeEvent
from nti.dataserver.interfaces import IDataserverTransactionRunner
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.entity import Entity
from nti.dataserver.users.entity import get_shared_dataserver

from nti.dataserver.users.interfaces import IRecreatableUser
from nti.dataserver.users.interfaces import _VERBOTEN_PASSWORDS
from nti.dataserver.users.interfaces import InsecurePasswordIsForbidden
from nti.dataserver.users.interfaces import PasswordCannotConsistOfOnlyWhitespace
from nti.dataserver.users.interfaces import OldPasswordDoesNotMatchCurrentPassword

from nti.dataserver.activitystream_change import Change

from nti.datastructures import datastructures

from nti.ntiids import ntiids

from nti.property.property import annotation_alias

from nti.zodb import minmax
from nti.zodb import isBroken

from nti.zodb.containers import time_to_64bit_int

# Starts as none, which matches what get_shared_dataserver takes as its
# clue to use get instead of query. But set to False or 0 to use
# query during evolutions.
BROADCAST_DEFAULT_DS = None

SharingTarget = sharing.SharingTargetMixin
deprecated('SharingTarget', 'Prefer sharing.SharingTargetMixin')

SharingSource = sharing.SharingSourceMixin
deprecated('SharingSource', 'Prefer sharing.SharingSourceMixin')

DynamicSharingTarget = sharing.DynamicSharingTargetMixin
deprecated('DynamicSharingTarget', 'Prefer sharing.DynamicSharingTargetMixin')

class _Password(object):
	"""
	Represents the password of a principal, as
	encoded by a password manager. Immutable.
	"""

	def __init__(self, password, manager_name='bcrypt'):
		"""
		Creates a password given the plain text and the name of a manager
		to encode it with.

		:key manager_name string: The name of the :class:`IPasswordManager` to use
			to manager this password. The default is ``bcrypt,`` which uses a secure,
			salted hash. This is the recommended manager. If it is not available (due to the
			absence of C extensions?) the ``pbkdf2`` manager can be used. See :mod:`z3c.bcrypt`
			and :mod:`zope.password`.
		"""

		manager = component.getUtility(IPasswordManager, name=manager_name)
		self.__encoded = manager.encodePassword(password)
		self.password_manager = manager_name

	def checkPassword(self, password):
		"""
		:return: Whether the given (plain text) password matches the
		encoded password stored by this object.
		"""
		manager = component.getUtility(IPasswordManager, name=self.password_manager)
		result = manager.checkPassword(self.__encoded, password)
		return result

	def getPassword(self):
		"""
		Like the zope pluggableauth principals, we allow getting the raw
		bytes of the password. Obviously these are somewhat valuable, even
		when encoded, so take care with them.
		"""
		return self.__encoded

	# Deliberately has no __eq__ method, passwords cannot
	# be directly compared outside the context of their
	# manager.

from .entity import named_entity_ntiid

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

		super(Principal, self).__init__(username,
									   parent=parent)
		if password:
			self.password = password

	def has_password(self):
		return bool(self.password)

	def _get_password(self):
		return self.__dict__.get('password', None)
	def _set_password(self, np):
		# TODO: Names for these?
		component.getUtility(pwd_interfaces.IPasswordUtility).verify(np)
		# NOTE: The password policy objects do not have an option to forbid
		# all whitespace, so we implement that manually here.
		# TODO: Subclass the policy and implement one that does, install that and migrate
		if np and not np.strip():  # but do allow leading/trailing whitespace
			raise PasswordCannotConsistOfOnlyWhitespace()
		# NOTE: The password policy objects do not have an option to forbid
		# specific passwords from a list, so we implement that manually here.
		# TODO: Subclass the policy and implement one that does, as per above
		if np and np.strip().upper() in _VERBOTEN_PASSWORDS:
			raise InsecurePasswordIsForbidden(np)

		self.__dict__['password'] = _Password(np, self.password_manager_name)
		# otherwise, no change
	def _del_password(self):
		del self.__dict__['password']
	password = property(_get_password, _set_password, _del_password)

	NTIID_TYPE = None
	NTIID = cachedIn('_v_ntiid')(named_entity_ntiid)

if os.getenv('DATASERVER_TESTING_PLAIN_TEXT_PWDS') == 'True':
	# For use by nti_run_integration_tests, nti_run_general_purpose_tests;
	# plain text passwords are much faster than bcrpyt, and since
	# the tests use HTTP Basic Auth, this makes a difference
	print("users.py: WARN: Configuring with plain text passwords", file=sys.stderr)
	Principal.password_manager_name = 'Plain Text'

from .communities import Everyone

from .entity import NOOPCM as _NOOPCM

from .friends_lists import FriendsList
from .friends_lists import DynamicFriendsList
from .friends_lists import _FriendsListMap  # BWC

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecated(
	"Import from nti.dataserver.users.communities.Community instead",
	Community='nti.dataserver.users.communities:Community')

zope.deferredimport.deprecatedFrom(
	"Moved to nti.dataserver.users.friends_lists",
	"nti.dataserver.users.friends_lists",
	"DynamicFriendsList",
	"_FriendsListUsernameIterable")

ShareableMixin = sharing.ShareableMixin
deprecated('ShareableMixin', 'Prefer sharing.ShareableMixin')

from .device import Device
from .device import _DevicesMap

@interface.implementer(ITranscriptContainer)
class _TranscriptsMap(datastructures.AbstractNamedLastModifiedBTreeContainer):
	contained_type = ITranscript
	container_name = 'Transcripts'
	__name__ = container_name

@interface.implementer(IContainerIterable,
						IUser,
						IIntIdIterable,
						ISublocations)
class User(Principal):
	"""A user is the central class for data storage. It maintains
	not only a few distinct pieces of data but also a collection of
	Contained items.

	All additions and deletions to Contained items
	go through the User class, which takes care of posting appropriate
	notifications to queues. For updates to contained objects,
	the methods beginUpdates() and endUpdates() must surround the updates. Objects
	retrieved from getObject() will be monitored for changes during this period
	and notifications posted at the end. Mutations to non-persistent data structurs
	may not be caught by this and so such objects should be explicitly marked
	as changed using setPersistentStateChanged().
	"""

	family = BTrees.family64
	_ds_namespace = 'users'
	mime_type = 'application/vnd.nextthought.user'

	@classmethod
	def get_user(cls, username, dataserver=None, default=None):
		"""
		Returns the User having ``username``, else None.

		:param basestring username: The username to find. Can also be an instance of
			this class, in which case it is immediately returned (effectively making this
			behave like a :mod:`zope.interface` cast. Note that it is this specific
			class, not :class:`User` in general.
		"""
		if isinstance(username, cls):
			return username
		result = cls.get_entity(username, dataserver=dataserver, default=default) if username else None
		return result if isinstance(result, User) else default  # but this instance check is the base class

	@classmethod
	def create_user(cls, dataserver=None, **kwargs):
		"""
		Creates (and returns) and places in the dataserver a new user,
		constructed using the keyword arguments given, the same as
		those the User constructor takes. Raises a :class:`KeyError`
		if the user already exists. You handle the transaction.
		"""
		return cls.create_entity(dataserver=dataserver, **kwargs)

	delete_user = Principal.delete_entity

	# External incoming ignoring and accepting can arrive in three ways.
	# As a list, which replaces the entire contents.
	# As a single string, which is added to the list.
	# As a dictionary with keys 'add' and 'remove', mapping to lists

	@classmethod
	def _resolve_entities(cls, dataserver, external_object, value):
		result = []
		if isinstance(value, basestring):
			result = cls.get_entity(value, dataserver=dataserver)
		elif isinstance(value, collections.Sequence):
			# A list of names or externalized-entity maps
			result = []
			for username in value:
				if isinstance(username, collections.Mapping):
					username = username.get('Username')
				entity = cls.get_entity(username, dataserver=dataserver)
				if entity: result.append(entity)
		elif isinstance(value, collections.Mapping):
			if value.get('add') or value.get('remove'):
				# Specified edits
				result = { 'add': cls._resolve_entities(dataserver, external_object, value.get('add')),
						   'remove': cls._resolve_entities(dataserver, external_object, value.get('remove')) }
			else:
				# a single externalized entity map
				result = cls.get_entity(value.get('Username'), dataserver=dataserver)

		return result

	__external_resolvers__ = { 'ignoring': _resolve_entities, 'accepting': _resolve_entities }

	# The last login time is an number of seconds (as with time.time).
	# When it gets reset, the number of outstanding notifications also
	# resets. It is writable, number is not...
	lastLoginTime = minmax.NumericPropertyDefaultingToZero(str('lastLoginTime'),
														   minmax.NumericMaximum,
														   as_number=True)
	# ...although, pending a more sophisticated notification tracking
	# mechanism, we are allowing notification count to be set...
	notificationCount = minmax.NumericPropertyDefaultingToZero(str('notificationCount'),
															   minmax.MergingCounter)

	# TODO: If no AvatarURL is set when externalizing,
	# send back a gravatar URL for the primary email:
	# http://www.gravatar.com/avatar/%<Lowercase hex MD5>=44&d=mm

	def __init__(self, username, password=None,

				 parent=None, _stack_adjust=0):
		super(User, self).__init__(username, password=password,
								  parent=parent)
		IUser['username'].bind(self).validate(self.username)
		# We maintain a Map of our friends lists, organized by
		# username (only one friend with a username)

		if self.__parent__ is None and component.queryUtility(IIntIds) is not None:
			warnings.warn(
				"No parent provided. User will have no Everyone list or Community; "
				"either use User.create_user or provide parent kwarg",
				stacklevel=(2 if type(self) == User else 3) + _stack_adjust)

		self.friendsLists = _FriendsListMap()
		self.friendsLists.__parent__ = self

		# Join our default community
		if self.__parent__:
			everyone = self.__parent__.get(Everyone._realname)
			if everyone:
				self.record_dynamic_membership(everyone)

		# We maintain a list of devices associated with this user
		# TODO: Want a persistent set?
		self.devices = _DevicesMap()
		self.devices.__parent__ = self

		# Create the containers, along with the initial set of contents.
		# Note that this doesn't reparent them, they stay parented by us
		# FIXME: We should be using a unique value for containerType (instead of
		# the generic CheckingLastModifiedBTreeContainer) so that we can
		# register adapters for these containers in a clean way.
		# FIXME: Why are we just using a dict instead of a btree implementation
		# for containersType? A user can (does) have many, many different
		# containers, so won't this pickle get too large?
		self.containers = datastructures.ContainedStorage(create=self,
														  containersType=dicts.CaseInsensitiveLastModifiedDict,
														  containers={self.friendsLists.container_name: self.friendsLists,
																	  self.devices.container_name: self.devices })
		self.containers.__parent__ = self
		self.containers.__name__ = ''  # TODO: This is almost certainly wrong. We hack around it

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
	def creator(self, other):
		""" Ignored. """
		return

	@property
	def containerId(self):
		return "Users"

	NTIID_TYPE = ntiids.TYPE_NAMED_ENTITY_USER

	def update_last_login_time(self):
		self.lastLoginTime = time.time()

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		# with self._NoChangeBroadcast( self ):
		super(User, self).updateFromExternalObject(parsed, *args, **kwargs)
		updated = None
		lastLoginTime = parsed.pop('lastLoginTime', None)
		if isinstance(lastLoginTime, numbers.Number) and self.lastLoginTime < lastLoginTime:
			self.lastLoginTime = lastLoginTime
			self.notificationCount = 0  # reset to zero. Note that we don't del the property to keep the same persistent object object
			updated = True

		notificationCount = parsed.pop('NotificationCount', None)
		if isinstance(notificationCount, numbers.Number):
			self.notificationCount = notificationCount
			updated = True

		if 'password' in parsed:
			old_pw = None
			if self.has_password():
				# To change an existing password, you must send the old
				# password (The default, empty string, is never a valid password and lets
				# us produce better error messages then having no default)
				old_pw = parsed.pop('old_password', '')
				# And it must match
				if not self.password.checkPassword(old_pw):
					raise OldPasswordDoesNotMatchCurrentPassword()
			password = parsed.pop('password')
			# TODO: Names/sites for these? That are distinct from the containment structure?
			component.getUtility(pwd_interfaces.IPasswordUtility).verify(password, old_pw)
			self.password = password  # NOTE: This re-verifies
			updated = True

		# Muting/Unmuting conversations. Notice that we only allow
		# a single thing to be changed at once. Also notice that we never provide
		# the full list of currently muted objects as external data. These
		# both support the idea that the use-case for this feature is a single button
		# in the UI at the conversation level, and that 'unmuting' a conversation is
		# only available /immediately/ after muting it, as an 'Undo' action (like in
		# gmail). Our muted conversations still show up in search results, as in gmail.
		if 'mute_conversation' in parsed:
			self.mute_conversation(parsed.pop('mute_conversation'))
			updated = True
		elif 'unmute_conversation' in parsed:
			self.unmute_conversation(parsed.pop('unmute_conversation'))
			updated = True

		# See notes on how ignoring and accepting values may arrive.
		def handle_ext(reset, add, value):
			if value:
				updated = True
				for x in value:
					reset(x)
					add(x)

		def set_from_input(field, existing, remove):
			"""
			Get our set from input. For targeted removes, go
			ahead and remove.
			"""
			value = parsed.pop(field, None)
			result = None
			if isinstance(value, collections.Sequence):
				result = set(value)
			elif isinstance(value, collections.Mapping):
				result = set(existing)
				for x in (value.get('add') or ()):
					result.add(x)
				for x in (value.get('remove') or ()):
					updated = True
					result.discard(x)
					remove(x)
			elif value is not None:
				result = set((value,))
			return result or set()

		# Allow targeted add/removals for ignoring/accepting. With this
		# order, accepts trump ignores (we may ignore a person and then
		# accept from them if they exist in both arrays).  We get our
		# incoming set (and remove specified drops) and then do any
		# new ignores or accepts.
		old_ignore = set(self.entities_ignoring_shared_data_from)
		ignoring = set_from_input('ignoring', old_ignore, self.stop_ignoring_shared_data_from)
		ignoring_diff = ignoring - old_ignore
		handle_ext(self.reset_shared_data_from,
					self.ignore_shared_data_from,
					ignoring_diff)

		old_accept = set(self.entities_accepting_shared_data_from)
		accepting = set_from_input('accepting', old_accept, self.stop_accepting_shared_data_from)
		accepting_diff = accepting - old_accept
		handle_ext(self.reset_shared_data_from,
					self.accept_shared_data_from,
					accepting_diff)
		return updated

	# ## Sharing

	def _get_dynamic_sharing_targets_for_read(self):
		"""
		Overrides the super method to return both the communities we are a
		member of, plus the friends lists we ourselves have created that are dynamic.
		"""
		result = set(super(User, self)._get_dynamic_sharing_targets_for_read())
		for fl in self.friendsLists.values():
			if IDynamicSharingTarget.providedBy(fl):
				result.add(fl)
		return result

	def _get_entities_followed_for_read(self):
		return set(super(User, self)._get_entities_followed_for_read())

	@Lazy
	def _circled_events_storage(self):
		"""
		Right now, normally change events are not owned by anyone,
		they are simply referenced from the stream cache based on the
		intid of the *changed* object. Events are not sent for change
		events otherwise and thus they do not get their own intid.

		We want to keep a history of circled events however and we want
		to index them. If we just send the events to do this, we wind
		up with \"orphan\" change events in the index and intid utilities
		(because they are not owned by anyone, when the user gets cleaned up,
		we wouldn't know to clean the events up).

		The solution is to store them here and return them as sublocations so that
		they do get cleaned up. We don't expect there to be many, so we
		use a simple list.
		"""
		self._p_changed = True
		result = PersistentList()
		result.__parent__ = self
		return result

	def accept_shared_data_from(self, source):
		""" Accepts if not ignored; auto-follows as well.
		:return: A truth value. If this was the initial add, it will be the Change.
			If the source is ignored, it will be False."""

		if self.is_ignoring_shared_data_from(source):
			return False
		already_accepting = super(User, self).is_accepting_shared_data_from(source)
		if super(User, self).accept_shared_data_from(source):
			if already_accepting:
				# No change
				return True

			# Broadcast a change for the first time we're circled by this person
			# TODO: Do we need to implement a limbo state, pending acceptance
			# by the person?
			change = Change(Change.CIRCLED, source)
			change.creator = source
			# Not anchored, show at root and below. This overrides
			# the containerId gained from the source.
			change.containerId = ''
			# Also override the parent attribute copied from the source
			# to be us so we can treat this object like one of our sublocations
			change.__parent__ = self
			assert change.__name__ == source.username
			change.useSummaryExternalObject = True  # Don't send the whole user

			# Now that it's all configured, store it, give it an intid, and let
			# it get indexed. Let listeners do things do it (e.g., notabledata).
			# We still keep ownership though (its parent is set to us)...
			# it's important to do this before going through _noticeChange, which will
			# further disseminate this event
			self._circled_events_storage.append(change)
			lifecycleevent.created(change)
			lifecycleevent.added(change)

			# Bypass the whole mess of broadcasting and going through the DS and change listeners,
			# and just notice the incoming change.
			# TODO: Clean this up, go back to event based.
			self._noticeChange(change)

			return change  # which is both True and useful

	def is_accepting_shared_data_from(self, source):
		""" We say we're accepting so long as we're not ignoring. """
		# TODO: the 'incoming' group discussed in super will obsolete this
		return not self.is_ignoring_shared_data_from(source)

	def getFriendsList(self, name):
		""" Returns the friends list having the given name, otherwise
		returns None. """
		return self.friendsLists.get(name)

	def getFriendsLists(self, name=None):
		""" Returns all the friends lists"""
		return tuple(self.friendsLists.values())

	def maybeCreateContainedObjectWithType(self, datatype, externalValue):
		if datatype in (self.devices.container_name, Device.mimeType):
			result = Device(externalValue)
		else:
			# FIXME: This is a hack to translate mimetypes to the old
			# style of name that works with self.containers
			if datatype in (FriendsList.mimeType, DynamicFriendsList.mimeType):
				datatype = self.friendsLists.container_name
			result = self.containers.maybeCreateContainedObjectWithType(datatype, externalValue)
		return result

	def addContainedObject(self, contained):
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
		if getattr(contained, '_p_jar', self) is None \
			and getattr(self, '_p_jar') is not None:
			self._p_jar.add(contained)

		result = self.containers.addContainedObject(contained)
		return result

	def deleteContainedObject(self, containerId, containedId):
		try:
			self.containers._p_activate()
			self.containers._p_jar.readCurrent(self.containers)
		except AttributeError:
			pass
		return self.containers.deleteContainedObject(containerId, containedId)

	# TODO: Could/Should we use proxy objects to automate
	# the update process? Allowing updates directly to deep objects?
	# What about monitoring the resources associated with the transaction
	# and if any of them belong to us posting a notification? (That seems
	# convenient but a poor separation of concerns)

	def getContainedObject(self, containerId, containedId, defaultValue=None):
		if containerId == self.containerId:  # "Users"
			return self
		return self.containers.getContainedObject(containerId, containedId, defaultValue)

	def getContainer(self, containerId, defaultValue=None, context_cache=None):
		stored_value = self.containers.getContainer(containerId, defaultValue)
		return stored_value

	def getAllContainers(self):
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
		if interface.interfaces.IInterface.providedBy(of_type):
			test = of_type.providedBy
		elif isinstance(of_type, six.class_types):
			test = lambda x: isinstance(x, of_type)
		else:
			test = lambda x: True

		for container in self.getAllContainers().values():
			if not hasattr(container, 'values'): continue
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
			if getattr(v, '__parent__', None) is self:
				yield v

		# Now our circled events, these need to get deleted/indexed etc
		for change in self._circled_events_storage:
			yield change

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
		# annotations = zope.annotation.interfaces.IAnnotations(self, {})

		# Technically, IAnnotations doesn't have to be iterable of values,
		# but it always is (see zope.annotation.attribute)
		# for val in annotations.values():
		# 	if getattr( val, '__parent__', None ) is self:
		# 		yield val

	def _is_container_ntiid(self, containerId):
		"""
		Filters out things that are not used as NTIIDs. In the future,
		this will be easy (as soon as everything is tag-based). Until then,
		we rely on the fact that all our custom keys are upper cased.
		"""
		return len(containerId) > 1 and \
			   (containerId.startswith('tag:nextthought.com')
				or containerId[0].islower())

	def iterntiids(self, include_stream=True, stream_only=False):
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
					seen.add(k)
					yield k

			for k in self.containersOfShared:
				if self._is_container_ntiid(k) and k not in seen:
					seen.add(k)
					yield k
		if include_stream:
			for k in self.streamCache:
				if self._is_container_ntiid(k) and k not in seen:
					seen.add(k)
					yield k

		fl_set = {x for x in self.friendsLists.values() if IDynamicSharingTarget.providedBy(x)}
		interesting_dynamic_things = set(self.dynamic_memberships) | fl_set
		for com in interesting_dynamic_things:
			if not stream_only and hasattr(com, 'containersOfShared'):
				for k in com.containersOfShared:
					if self._is_container_ntiid(k) and k not in seen:
						seen.add(k)
						yield k
			if include_stream and hasattr(com, 'streamCache'):
				for k in com.streamCache:
					if self._is_container_ntiid(k) and k not in seen:
						seen.add(k)
						yield k

	def iter_containers(self):
		# TODO: Not sure about this. Who should be responsible for
		# the UGD containers? Should we have some different layout
		# for that (probably).
		return (v
				for v in self.containers.containers.itervalues()
				if INamedContainer.providedBy(v))
	itercontainers = iter_containers

	def iter_objects(self, include_stream=True, stream_only=False,
					 include_shared=False, only_ntiid_containers=False):

		def _loop(container, unwrap=False):
			if hasattr(container, 'values'):
				collection = container.values()
			else:
				collection = container
			for obj in collection:
				obj = self.containers._v_unwrap(obj) if unwrap else obj
				if isBroken(obj):
					logger.error("ignoring broken object %s", type(obj))
				else:
					yield obj

		if not stream_only:
			for name, container in self.containers.iteritems():
				if not only_ntiid_containers or self._is_container_ntiid(name):
					for obj in _loop(container, True):
						yield obj

		if include_stream:
			for name, container in self.streamCache.iteritems():
				if not only_ntiid_containers or self._is_container_ntiid(name):
					for obj in _loop(container, False):
						yield obj

		if include_shared:
			fl_set = {x for x in self.friendsLists.values()
					  if IDynamicSharingTarget.providedBy(x) }

			interesting_dynamic_things = set(self.dynamic_memberships) | fl_set
			for com in interesting_dynamic_things:
				if not stream_only and hasattr(com, 'containersOfShared'):
					for name, container in com.containersOfShared.items():
						if not only_ntiid_containers or self._is_container_ntiid(name):
							for obj in _loop(container, False):
								yield obj

				if include_stream and hasattr(com, 'streamCache'):
					for name, container in com.streamCache.iteritems():
						if not only_ntiid_containers or self._is_container_ntiid(name):
							for obj in _loop(container, False):
								yield obj

	def iter_intids(self, include_stream=True, stream_only=False,
					include_shared=False, only_ntiid_containers=False):
		seen = set()
		intid = component.getUtility(IIntIds)
		for obj in self.iter_objects(include_stream=include_stream,
									 stream_only=stream_only,
									 include_shared=include_shared,
									 only_ntiid_containers=only_ntiid_containers):

				uid = intid.queryId(obj)
				if uid is not None and uid not in seen:
					seen.add(uid)
					yield uid

	def updates(self):
		"""
		This is officially deprecated now.

		noisy if enabled; logic in flagging_views still needs its existence until rewritten
		"""
		return _NOOPCM

	def _acceptIncomingChange(self, change, direct=True):
		accepted = super(User, self)._acceptIncomingChange(change, direct=direct)
		if accepted:
			self.notificationCount.increment()
			self._broadcastIncomingChange(change)

	def _broadcastIncomingChange(self, change):
		"""
		Distribute the incoming change to any connected devices/sessions.
		This is an extension point for layers.
		"""
		# TODO: Move this out to a listener somewhere
		apnsCon = component.queryUtility(apns_interfaces.INotificationService)
		# NOTE: At this time, no such component is actually
		# being registered.
		if not apnsCon:
			if self.devices:
				logger.warn("No APNS connection, not broadcasting change")
			return
		if self.devices:
			from nti.apns.payload import APNSPayload
			# If we have any devices, notify them
			userInfo = None
			if change.containerId:
				# Valid NTIIDs are also valid URLs; this
				# condition is mostly for legacy code (tests)
				if ntiids.is_valid_ntiid_string(change.containerId):
					userInfo = {'url:': change.containerId }

			payload = APNSPayload(badge=self.notificationCount.value,
								   sound='default',
								   # TODO: I18N text for this
								   alert='An object was shared with you',  # change.creator.preferredDisplayName + ' shared an object',
								   userInfo=userInfo)
			for device in self.devices.itervalues():
				if not isinstance(device, Device):
					continue
				__traceback_info__ = device, payload, change
				try:
					apnsCon.sendNotification(device.deviceId, payload)
				except Exception:  # Big catch: this is not crucial, we shouldn't hurt anything without it
					logger.exception("Failed to send APNS notification")

	def _xxx_extra_intids_of_memberships(self):
		# We want things shared with the DFLs we own to be counted
		# as visible to us
		for x in self.friendsLists.values():
			if IDynamicSharingTargetFriendsList.providedBy(x):
				# Direct access is a perf optimization, this is called a lot
				yield x._ds_intid

# We have a few subclasses of User that store some specific
# information and directly implement some interfaces.
# Right now, we're not exposing this information directly to clients,
# so this is an implementation detail. Thus we make their class names
# be 'User' as well.
# TODO: MimeTypes?

@interface.implementer(IOpenIdUser)
class OpenIdUser(User):
	__external_class_name__ = 'User'

	identity_url = None

	def __init__(self, username, **kwargs):
		id_url = kwargs.pop('identity_url', None)
		super(OpenIdUser, self).__init__(username, **kwargs)
		if id_url:
			self.identity_url = id_url

@interface.implementer(IFacebookUser)
class FacebookUser(User):
	__external_class_name__ = 'User'
	facebook_url = None

	def __init__(self, username, **kwargs):
		id_url = kwargs.pop('facebook_url', None)
		super(FacebookUser, self).__init__(username, **kwargs)
		if id_url:
			self.facebook_url = id_url

@component.adapter(apns_interfaces.IDeviceFeedbackEvent)
def user_devicefeedback(msg):
	def feedback():
		deviceId = msg.deviceId
		hexDeviceId = deviceId.encode('hex')
		# TODO: Very inefficient
		# Switch this to ZCatalog/repoze.catalog
		if msg.timestamp < 0: return
		datasvr = get_shared_dataserver()
		logger.debug('Searching for device %s', hexDeviceId)
		for user in (u for u in datasvr.root['users'].itervalues() if isinstance(u, User)):
			if hexDeviceId in user.devices:
				logger.debug('Found device id %s in user %s', hexDeviceId, user)
				del user.devices[hexDeviceId]

	# Be sure we run in the right site and transaction.
	# Our usual caller is in nti.apns and knows nothing about that.
	# NOTE: We are not using a site policy here so the listener is limited
	if IConnection(component.getSiteManager(), None):
		feedback()
	else:
		component.getUtility(IDataserverTransactionRunner)(feedback)

@component.adapter(ITargetedStreamChangeEvent)
def onChange(event):
	entity = event.entity
	msg = event.object
	if hasattr(entity, '_noticeChange'):
		try:
			entity._p_activate()
			entity._p_jar.readCurrent(entity)
		except AttributeError:
			pass
		entity._noticeChange(msg)

@interface.implementer(IZContained)
@interface.implementer(IUserBlacklistedStorage)
class UserBlacklistedStorage(Persistent):
	"""
	Stores deleted/blacklisted usernames case-insensitively in a btree
	to their int-encoded delete times.
	"""

	def __init__(self):
		self._storage = BTrees.OLBTree.BTree()

	def _get_user_key(self, user):
		username = getattr(user, 'username', user)
		return username.lower()

	def blacklist_user(self, user):
		now = time.time()
		user_key = self._get_user_key(user)
		self._storage[user_key] = time_to_64bit_int(now)
	add = blacklist_user

	def is_user_blacklisted(self, user):
		user_key = self._get_user_key(user)
		return user_key in self._storage
	__contains__ = is_user_blacklisted

	def remove_blacklist_for_user(self, username):
		result = False
		try:
			del self._storage[username]
			result = True
		except KeyError:
			pass
		return result
	remove = remove_blacklist_for_user

	def clear(self):
		self._storage.clear()
	reset = clear

	def __iter__(self):
		return iter(self._storage.items())

	def __len__(self):
		return len(self._storage)

@component.adapter(IUser, IObjectRemovedEvent)
def _blacklist_username(user, event):
	username = user.username
	if 		not IRecreatableUser.providedBy(user) \
		and not username.lower().endswith('@nextthought.com'):
		user_blacklist = component.getUtility(IUserBlacklistedStorage)
		user_blacklist.blacklist_user(user)
		logger.info("Black-listing username %s", username)

@component.adapter(IUser)
@interface.implementer(IUserDigestEmailMetadata)
class _UserDigestEmailMetadata(object):
	"""
	Holds digest email user metadata times.
	"""

	def __init__(self, user):
		self.parent = user.__parent__
		self.user_key = self._get_user_key( user )

	def _get_user_key(self, user):
		intids = component.getUtility(IIntIds)
		user_intid = intids.getId( user )
		return user_intid

	_DIGEST_META_KEY = 'nti.dataserver.users.UsersDigestEmailMetadata'
	_user_meta_storage = annotation_alias(_DIGEST_META_KEY,
										annotation_property='parent',
										doc="The time metadata storage on the users folder")

	def _get_meta_storage(self):
		if not self._user_meta_storage:
			self._user_meta_storage = PersistentMapping()
		return self._user_meta_storage

	def _get_last_collected(self):
		# last_collected is index 0
		meta_storage = self._get_meta_storage()
		try:
			result = meta_storage[self.user_key]
			result = result[0]
		except KeyError:
			result = 0
		return result

	def _set_last_collected(self, update_time):
		meta_storage = self._get_meta_storage()
		try:
			user_data = meta_storage[self.user_key]
			user_data = (update_time, user_data[1])
		except KeyError:
			user_data = (update_time, 0)
		meta_storage[self.user_key] = user_data

	def _get_last_sent(self):
		# last_sent is index 1
		meta_storage = self._get_meta_storage()
		try:
			result = meta_storage[self.user_key]
			result = result[1]
		except KeyError:
			result = 0
		return result

	def _set_last_sent(self, update_time):
		meta_storage = self._get_meta_storage()
		try:
			user_data = meta_storage[self.user_key]
			user_data = (user_data[0], update_time)
		except KeyError:
			user_data = (0, update_time)
		meta_storage[self.user_key] = user_data

	last_sent = property(_get_last_sent, _set_last_sent)
	last_collected = property(_get_last_collected, _set_last_collected)

@component.adapter(IUser, IObjectRemovedEvent)
def _digest_email_remove_user(user, unused_event):
	user_metadata = component.getUtility(IUserDigestEmailMetadata)
	user_metadata.remove_user_data(user)
