#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Transcripts for chats as stored on users.

The object model
================

The concept of a meeting room is something that can contain resources.
Meeting rooms hold meetings (at most one meeting at a time). The
meetings are transcripted and this transcript is attached as a
resource to the room. A meeting's ContainerID is the ID of the room.
Within a meeting, a MessageInfo's ContainerID is the ID of the
meeting. Some meetings take place "in the hallway" or "around the
cooler" and as such belong to no room. When they finish, the
transcript is accessible just to the users that participated. (These
meetings may still have ContainerIDs of other content, and they will
be accessible from that location, as is anything contained there.)


Garbage Collection
===================

Currently, users are stored in a different database than Meeting and
MessageInfo objects (which are together with sessions). If that
database is packed and GC'd without using zc.zodbgc to do a multi-GC,
then we can lose all our transcripts. It's not as simple as just
moving those objects to the User database, either, because we may be
sharded. The approach to solving the problem, then, is to keep
/explicit/ weak refs and use them as long as possible (TODO: Does that
still break with zc.zodbgc?), but also make a copy in our database to
fallback on (in some cases, the objects are mutated after being
transcripted so the copy may not be perfectly in sync or we'd always
just use it). Note that this must be a deep copy: these are persistent
objects with sub-objects stored in the same initial database, and a
shallow copy would fail after GC for the same reasons as the original
object. Consequently, we use zope.copy for its deep-copy approach (via
pickling) in addition to its hooks support.

This is unfortunately quite a bit more expensive than strictly necessary:

* Profiling shows that the reference and the copy **double** the
  amount of time spent storing transcripts. Most of that time is in
  the copy itself
* Using a KeyReferenceToPersistent as the messages key amounts to a
  third of the cost.
* Using int ids for the messages an 64-bit IOBTree shaves 20% or so of
  the cost relative to an OOBTree and the string UUID of the message
* In a 12-second, 5000 msg, 4 user test (without copy), half the time
  is in committing, and one third is spent in serializing so
  simplifying the MessageInfo objects might be worth it, but there's
  not much to simplify.
* As of 2012-07-26, that same 5000 msg, 4-user test, through the use
  of pervasive intids, and sharing datastructure changes, is down to
  5.5 seconds instead of 12.
* Making MessageInfo non-Persistent substantially increases the
  runtime (back to copy levels, because it does amount to making
  copies)

In light of this info, given that transcript storage is a performance
sensitive operation, and that (a) we know how to run GCs cross
database without losing refs either using zc.zodbcgc or simply having
the storage keep all non-historical objects, and that RelStorage
reduces the need to run GC anyway, we opt to reverse the previous
policy and simply store a weak ref.

Experiments with using intids and an IISet in MeetingTranscriptStorage
were a wash, as were using an OOTreeSet instead of an OOBTree. The
biggest win is simply reducing all the transactions to one. There's
probably a big win in unifying the indexes. Try an KeywordIndex.

"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )

from nti.ntiids import ntiids
from nti.dataserver.activitystream_change import Change
from nti.dataserver.activitystream import enqueue_change
from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.dataserver import mimetype
from nti.dataserver import users
from nti.dataserver import datastructures
from nti.dataserver import links

import nti.externalization.datastructures
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization import interfaces as ext_interfaces

import persistent.wref
from persistent import Persistent
import BTrees.OOBTree
import ZODB.POSException

from zope import interface
from zope import component
from zope import intid
from zope.cachedescriptors.property import CachedProperty


from nti.zodb.wref import CopyingWeakRef as _CopyingWeakRef # bwc for things in the database

class _IMeetingTranscriptStorage(interface.Interface):
	pass

@interface.implementer(_IMeetingTranscriptStorage)
class _AbstractMeetingTranscriptStorage(Persistent,datastructures.ZContainedMixin,datastructures.CreatedModDateTrackingObject):
	"""
	The storage for the transcript of a single session. Private object, not public.
	"""

	creator = nti_interfaces.SYSTEM_USER_NAME

	def __init__( self, meeting ):
		super(_AbstractMeetingTranscriptStorage,self).__init__()
		self._meeting_ref = persistent.wref.WeakRef( meeting )

	@property
	def meeting(self):
		return self._meeting_ref()

	def add_message( self, msg ):
		"""
		Stores the message in this transcript.
		"""
		raise NotImplementedError()

	def itervalues(self):
		raise NotImplementedError()

	# for finding MessageInfos with zope.genartions.findObjectsMatching
	# In some (early!) migration cases, it may be needed to disable this due to the switch to callable refs: the iterator cannot
	# iterate non-callable objects, and that breaks generations.findObjectsMatching,
	# it doesn't catch that exception.
	# Instead, the migration code needs to modify this class dynamically.
	def values(self):
		return self.itervalues()



@interface.implementer(_IMeetingTranscriptStorage)
class _MeetingTranscriptStorage(_AbstractMeetingTranscriptStorage):
	"""
	The storage for the transcript of a single session. Private object, not public.
	"""

	def __init__( self, meeting ):
		super(_MeetingTranscriptStorage,self).__init__(meeting)
		# To help avoid conflicts, messages
		# are stored keyed by their ID.
		# Getting an ordered list as thus an expensive
		# process. We COULD save the ordered list
		# after the room is closed, but right now rooms
		# are very rarely closed
		self.messages = BTrees.OOBTree.OOBTree()

	def add_message( self, msg ):
		"""
		Stores the message in this transcript.
		"""
		self.messages[msg.ID] = persistent.wref.WeakRef( msg )

	def itervalues(self):
		return (msg() for msg in self.messages.itervalues())


@interface.implementer(_IMeetingTranscriptStorage)
class _DocidMeetingTranscriptStorage(_AbstractMeetingTranscriptStorage):
	"""
	The storage for the transcript of a single session based on docids. Private object, not public.
	"""

	def __init__( self, meeting ):
		super(_DocidMeetingTranscriptStorage,self).__init__(meeting)
		family = getattr( self._intids, 'family', BTrees.family64 )
		self.messages = family.II.TreeSet()

	def add_message( self, msg ):
		"""
		Stores the message in this transcript.
		"""
		# TODO: Can/Should we start assuming this object exists
		# and use getId?
		self.messages.add( self._intids.getId( msg ) )

	def itervalues(self):
		intids = self._intids
		for iid in self.messages:
			msg = intids.queryObject( iid )
			if msg is not None:
				yield msg

	@CachedProperty
	def _intids(self):
		return component.getUtility( intid.IIntIds )


from repoze.lru import lru_cache
@lru_cache(10000)
def _transcript_ntiid( meeting, creator_username=None, nttype=ntiids.TYPE_TRANSCRIPT_SUMMARY ):
	"""
	:return: A NTIID string representing the transcript (summary) for the
		given meeting (chat session) with the given participant.
	"""
	return ntiids.make_ntiid( base=meeting.id,
							  provider=creator_username,
							  nttype=nttype )

def _get_by_oid(*args,**kwargs):
	return None
_get_by_oid.get_by_oid = _get_by_oid

@interface.implementer(chat_interfaces.IUserTranscriptStorage)
@component.adapter(nti_interfaces.IUser)
class _UserTranscriptStorageAdapter(object):
	"""
	The storage for all of a user's transcripts.

	You can look up transcripts by meeting ID.

	"""

	def __init__( self, user ):
		self._user = user

	def transcript_for_meeting( self, object_id ):
		result = None
		meeting_oid = object_id
		if not ntiids.is_ntiid_of_type( meeting_oid, ntiids.TYPE_OID ):
			# We'll take any type, usually a TRANSCRIPT type
			meeting_oid = ntiids.make_ntiid( base=meeting_oid,
											 provider=nti_interfaces.SYSTEM_USER_NAME,
											 nttype=ntiids.TYPE_OID )

		meeting = ntiids.find_object_with_ntiid( meeting_oid )
		if meeting is not None:
			storage_id = _transcript_ntiid( meeting, self._user.username )
			storage = self._user.getContainedObject( meeting.containerId, storage_id )
			result = Transcript( storage ) if storage else None
		else:
			# OK, the meeting has gone away, GC'd and no longer directly referencable.
			# Try to find the appropriate storage manually
			# TODO: finish converting this all to intids

			# We will accept either a match for the OID (unlikely at this point)
			# the original object_id (commonly a UUID during testing), or,
			# if we were given a TRANSCRIPT type, then we make a UUID (again,
			# for testing). We also accept a provider-mismatch for UUID values (again, testing)
			acceptable_oids = (meeting_oid, object_id)
			specific = ntiids.get_specific( object_id )
			if ntiids.is_ntiid_of_type( object_id, ntiids.TYPE_TRANSCRIPT ):
				acceptable_oids += (ntiids.make_ntiid( base=object_id, nttype=ntiids.TYPE_UUID ), )

			for value in self._user.values( of_type=_IMeetingTranscriptStorage ):
				value_meeting_id = value.meeting.ID
				if value_meeting_id in acceptable_oids or (ntiids.is_ntiid_of_type(value_meeting_id, ntiids.TYPE_UUID)
														   and ntiids.get_specific( value_meeting_id ) == specific ):
					result = Transcript( value )
					break

		return result

	@property
	def transcript_summaries( self ):
		result = []
		for container in self._user.getAllContainers().values():
			if isinstance( container, float ): continue
			for storage in container.values():
				if _IMeetingTranscriptStorage.providedBy( storage ):
					result.append( TranscriptSummaryAdapter( storage ) )
		return result

	def add_message( self, meeting, msg ):
		if not meeting.containerId:
			logger.warn( "Meeting (room) has no container id, will not transcript %s", meeting )
			# Because we won't be able to store the room on the user.
			# This is actually a bug in creating the room.
			return False

		# Our transcript storage we store with the
		# provider ID of our user
		storage_id = _transcript_ntiid( meeting, self._user.username )
		storage = self._user.getContainedObject( meeting.containerId, storage_id )
		if storage is None:
			# For old tests and old databases that are not migrated yet
			# we can make the switch at runtime
			storage_factory = _DocidMeetingTranscriptStorage if component.queryUtility( intid.IIntIds ) is not None else _MeetingTranscriptStorage
			storage = storage_factory( meeting )
			storage.id = storage_id
			storage.containerId = meeting.containerId
			storage.creator = self._user
			self._user.addContainedObject( storage )

		storage.add_message( msg )
		return storage

@interface.implementer(chat_interfaces.IUserTranscriptStorage)
class _MissingStorage(object):
	"""
	A storage that's always empty and blank.
	"""

	def transcript_for_meeting( self, meeting_id ):
		return None # pragma: no cover
	@property
	def transcript_summaries(self):
		return () # pragma: no cover
	def add_message( self, meeting, msg ):
		pass

_BLANK_STORAGE = _MissingStorage()

def _ts_storage_for( owner ):
	user = users.User.get_user( owner )
	storage = component.queryAdapter( user, chat_interfaces.IUserTranscriptStorage, default=_BLANK_STORAGE )
	return storage


@component.adapter( chat_interfaces.IMessageInfo, chat_interfaces.IMessageInfoPostedToRoomEvent )
def _save_message_to_transcripts_subscriber( msg_info, event ):
	"""
	Event handler that saves messages to the appropriate transcripts.
	"""
	meeting = event.room

	change = Change( Change.CREATED, msg_info )
	change.creator = msg_info.Sender

	for owner in set(event.recipients):
		__traceback_info__ = owner
		storage = _ts_storage_for( owner )
		storage.add_message( meeting, msg_info )

		# TODO: I think we are broadcasting this strictly for the sake of
		# getting it into the contentsearch indexes. Is this actually necessary? Could
		# or should contentsearch piggyback other events?
		enqueue_change( change, username=owner, broadcast=True )


def transcript_for_user_in_room( username, room_id ):
	"""
	Returns a :class:`Transcript` for the user in room.
	If the user wasn't in the room, returns None.
	"""
	storage = _ts_storage_for( username )
	return storage.transcript_for_meeting( room_id )


def transcript_summaries_for_user_in_container( username, containerId ):
	"""
	Primarily intended for debugging

	:return: Map of room/transcript id to :class:`TranscriptSummary` objects for the user that
		have taken place in the given containerId. The map will have attributes `lastModified`
		and `creator`.

	"""
	storage = _ts_storage_for( username )

	data = {summary.RoomInfo.ID: summary
			for summary
			in storage.transcript_summaries
			if summary.RoomInfo.containerId == containerId}
	logger.debug( "All summaries %s", data )
	result = LocatedExternalDict( data )
	result.creator = username
	if data:
		result.lastModified = max( data.itervalues(), key=lambda x: x.LastModified ).LastModified
	return result

def list_transcripts_for_user( username ):
	"""
	Returns an Iterable of :class:`TranscriptSummary` objects for the user.
	"""
	storage = _ts_storage_for( username )
	return storage.transcript_summaries

@interface.implementer(nti_interfaces.ITranscriptSummary, ext_interfaces.IInternalObjectIO)
@component.adapter(_IMeetingTranscriptStorage)
def TranscriptSummaryAdapter(meeting_storage):
	"""
	Registered as a ZCA adapter factory to get a :class:`nti_interfaces.ITranscriptSummary` (which is incidentally
	an :class:`ext_interfaces.IInternalObjectIO`).

	Deals gracefully with bad meeting storage objects that are missing components
	such as a room due to GC.
	"""
	try:
		if meeting_storage is not None and meeting_storage.meeting is not None:
			return TranscriptSummary(meeting_storage)
	except (ZODB.POSException.POSKeyError,AssertionError): # pragma: no cover
		logger.exception( "Meeting object gone missing." )
		return None


class TranscriptSummary(nti.externalization.datastructures.ExternalizableInstanceDict):
	"""
	The transcript summary for a user in a room.
	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.IZContained,
						 nti_interfaces.ILinked,
						 nti_interfaces.ITranscriptSummary,
						 ext_interfaces.IInternalObjectIO) # TODO: Strip this out, make schema driven

	__parent__ = None
	links = ()
	_NTIID_TYPE_ = ntiids.TYPE_TRANSCRIPT_SUMMARY

	def __init__( self, meeting_storage ):
		"""
		:param _IMeetingTranscriptStorage meeting_storage: The storage for the user in the room.
		"""
		super(TranscriptSummary,self).__init__( )
		room = meeting_storage.meeting
		assert room
		assert room.ID
		self.creator = meeting_storage.creator
		self.RoomInfo = room
		self.ContainerId = room.ID
		self.NTIID = None
		#if ntiids.is_ntiid_of_type( room.containerId, ntiids.TYPE_MEETINGROOM ):
			#self.NTIID = _transcript_ntiid( room, self.creator, self._NTIID_TYPE_ )
		self.NTIID = _transcript_ntiid( room, self.creator.username, self._NTIID_TYPE_ )
		_messages = list( meeting_storage.itervalues() )
		# TODO: What should the LastModified be? The room doesn't
		# currently track it. We're using the max for our messages, which may not be right?
		if _messages:
			m = max(_messages, key=lambda m: getattr(m, 'LastModified', 0))
			self.LastModified = getattr(m, 'LastModified', 0 )
		else:
			# cannot max() empty sequence
			self.LastModified = 0

		self.Contributors = set()
		for msg in _messages:
			self.Contributors.update( getattr(msg, 'sharedWith', ()) or () )

		self.links = self._create_links( meeting_storage )

	def _create_links( self, meeting_storage ):
		# TODO: constant
		return (links.Link( Transcript( meeting_storage ), rel="transcript" ),)

	@property
	def __name__(self):
		return self.NTIID

class Transcript(TranscriptSummary):
	"""
	The transcript for a user in a room.
	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.ITranscript)


	_NTIID_TYPE_ = ntiids.TYPE_TRANSCRIPT

	def __init__( self, meeting_storage ):
		"""
		:param _MeetingTranscriptStorage meeting_storage: The storage for the user in the room.
		"""
		super(Transcript,self).__init__( meeting_storage )
		# TODO: Make loading these lazy, since we are
		# creating these for links in summaries
		self.Messages = list( meeting_storage.itervalues() )

	def _create_links( self, meeting_storage ):
		return ()

	def __len__( self ):
		return len( self.Messages )

	def get_message( self, msg_id ):
		"""
		:return: The message in the transcript with the given ID, or None.
		"""
		for m in self.Messages:
			if m.ID == msg_id:
				return m
