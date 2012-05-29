#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Chatserver functionality. """
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

import persistent.wref
from persistent import Persistent
import BTrees.OOBTree
import ZODB.POSException

from zope import interface
from zope import component


####
# A note on the object model:
# The concept of a meeting room is something that can contain resources.
# Meeting rooms hold meetings (at most one meeting at a time). The meetings
# are transcripted and this transcript is attached as a resource to the room.
# A meeting's ContainerID is the ID of the room. Within a meeting, a MessageInfo's
# ContainerID is the ID of the meeting.
# Some meetings take place "in the hallway" or "around the cooler" and
# as such belong to no room. When they finish, the transcript is
# accessible just to the users that participated. (These meetings
# may still have ContainerIDs of other content, and they will be accessible
# from that location, as is anything contained there.)
####

###
# A Note on GC
# Currently, users are stored in a different database than
# Meeting and MessageInfo objects (which are together with sessions).
# If that database is packed and GC'd without using zc.zodbgc to do a multi-GC,
# then we can lose all our transcripts. It's not as simple as just moving
# those objects to the User database, either, because we may be sharded.
# The approach to solving the problem, then, is to keep /explicit/ weak refs and use
# them as long as possible (TODO: Does that still break with zc.zodbgc?),
# but also make a copy in our database to fallback on (in some cases, the objects are mutated
# after being transcripted so the copy may not be perfectly in sync or we'd
# always just use it). Note that this must be a deep copy: these are persistent
# objects with sub-objects stored in the same initial database, and a shallow
# copy would fail after GC for the same reasons as the original object. Consequently,
# we use zope.copy for its deep-copy approach (via pickling) in addition to its hooks support.
# This is unfortunately a bit more expensive than strictly necessary.
###
from zope import copy

class _CopyingWeakRef(persistent.wref.WeakRef):
	"""
	A weak ref that also stores a one-shot copy of its
	reference, as a fallback.
	"""
	def __init__( self, ob ):
		super(_CopyingWeakRef,self).__init__( ob )
		self._copy = copy.copy( ob )

	def __call__( self ):
		result = super(_CopyingWeakRef,self).__call__( )
		if result is None: result = self._copy
		return result

class _MeetingTranscriptStorage(Persistent,datastructures.ZContainedMixin,datastructures.CreatedModDateTrackingObject):
	"""
	The storage for the transcript of a single session. Private object, not public.
	"""

	creator = nti_interfaces.SYSTEM_USER_NAME

	def __init__( self, meeting ):
		super(_MeetingTranscriptStorage,self).__init__()
		# To help avoid conflicts, messages
		# are stored keyed by their ID.
		# Getting an ordered list as thus an expensive
		# process. We COULD save the ordered list
		# after the room is closed.
		self.messages = BTrees.OOBTree.OOBTree()
		# TODO: Use an IContainer?
		self._meeting_ref = _CopyingWeakRef(meeting)

	@property
	def meeting(self):
		return self._meeting_ref()

	def add_message( self, msg ):
		self.messages[msg.ID] = _CopyingWeakRef( msg )

	def itervalues(self):
		result = []
		for msg in self.messages.itervalues():
			if callable(msg):
				result.append(msg())
			else:
				result.append(msg)
		return tuple(result)

	# for finding MessageInfos with zope.genartions.findObjectsMatching
	# Currently disabled due to the switch to callable refs: the iterator cannot
	# iterate non-callable objects, and that breaks generations.findObjectsMatching,
	# it doesn't catch that exception
	#values = itervalues

def _transcript_ntiid( meeting, creator, nttype=ntiids.TYPE_TRANSCRIPT_SUMMARY ):
	"""
	:return: A NTIID string representing the transcript (summary) for the
		given meeting (chat session) with the given participant.
	"""
	return ntiids.make_ntiid( base=meeting.id,
							  provider=(creator.username if creator else None),
							  nttype=nttype )

def _get_by_oid(*args,**kwargs):
	return None
_get_by_oid.get_by_oid = _get_by_oid

class _UserTranscriptStorageAdapter(object):
	"""
	The storage for all of a user's transcripts.

	You can look up transcripts by meeting ID.

	"""

	interface.implements(chat_interfaces.IUserTranscriptStorage)
	component.adapts(users.User)

	def __init__( self, user ):
		self._user = user

	def transcript_for_meeting( self, object_id ):
		result = None
		meeting_id = object_id
		if not ntiids.is_ntiid_of_type( meeting_id, ntiids.TYPE_OID ):
			# We'll take any type, usually a TRANSCRIPT type
			meeting_id = ntiids.make_ntiid( base=meeting_id,
											provider=nti_interfaces.SYSTEM_USER_NAME,
											nttype=ntiids.TYPE_OID )

		meeting = component.queryUtility( nti_interfaces.IDataserver, default=_get_by_oid ).get_by_oid( meeting_id, ignore_creator=True )
		if meeting is not None:
			storage_id = _transcript_ntiid( meeting, self._user )
			storage = self._user.getContainedObject( meeting.containerId, storage_id )
			result = Transcript( storage ) if storage else None
		else:
			# OK, the meeting has gone away, GC'd and no longer directly referencable.
			# Try to find the appropriate storage manually
			for value in self._user.values( of_type=_MeetingTranscriptStorage ):
				if value.meeting.ID == meeting_id:
					result = Transcript( value )
					break
		return result

	@property
	def transcript_summaries( self ):
		result = []
		for container in self._user.getAllContainers().values():
			if isinstance( container, float ): continue
			for storage in container.values():
				if isinstance(storage, _MeetingTranscriptStorage):
					result.append( TranscriptSummaryAdapter( storage ) )
		return result

	def add_message( self, meeting, msg, ):
		assert msg.containerId
		assert msg.containerId == meeting.ID
		# Our transcript storage we store with the
		# provider ID of our user
		storage_id = _transcript_ntiid( meeting, self._user )
		storage = self._user.getContainedObject( meeting.containerId, storage_id )
		if not storage:
			if not meeting.containerId:
				logger.warn( "Meeting (room) has no container id, will not transcript %s", storage_id )
				# Because we won't be able to store the room on the user.
				# This is actually a bug in creating the room.
				return False

			storage = _MeetingTranscriptStorage( meeting )
			storage.id = storage_id
			storage.containerId = meeting.containerId
			storage.creator = self._user
			self._user.addContainedObject( storage )

		storage.add_message( msg )

class _MissingStorage(object):
	"""
	A storage that's always empty and blank.
	"""
	interface.implements(chat_interfaces.IUserTranscriptStorage)

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

def _save_message_to_transcripts( meeting, msg_info, transcript_names, transcript_owners=() ):
	"""
	Adds the message to the transcripts of each user given.

	:param MessageInfo msg_info: The message. Must have a container id.
	:param iterable transcript_names: Iterable of usernames to post the message to.
	:param iterable transcript_owners: Iterable of usernames to post the message to.
	"""
	owners = set( transcript_owners )
	owners.update( set(transcript_names) )

	change = Change( Change.CREATED, msg_info )
	change.creator = msg_info.Sender

	for owner in owners:
		storage = _ts_storage_for( owner )
		storage.add_message( meeting, msg_info )

		enqueue_change( change, username=owner, broadcast=True )

@component.adapter( chat_interfaces.IMessageInfo, chat_interfaces.IMessageInfoPostedToRoomEvent )
def _save_message_to_transcripts_subscriber( msg_info, event ):
	"""
	Event handler that saves messages to the appropriate transcripts.
	"""
	_save_message_to_transcripts( event.room, msg_info, event.recipients )

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

	EOM
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


def TranscriptSummaryAdapter(meeting_storage):
	try:
		return TranscriptSummary(meeting_storage)
	except ZODB.POSException.POSKeyError: # pragma: no cover
		logger.exception( "Meeting object gone missing." )
		return None

class TranscriptSummary(nti.externalization.datastructures.ExternalizableInstanceDict):
	"""
	The transcript summary for a user in a room.
	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.ILocation,
						 nti_interfaces.ILinked,
						 nti_interfaces.ITranscriptSummary)

	__parent__ = None
	links = ()
	_NTIID_TYPE_ = ntiids.TYPE_TRANSCRIPT_SUMMARY

	def __init__( self, meeting_storage ):
		"""
		:param _MeetingTranscriptStorage meeting_storage: The storage for the user in the room.
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
		self.NTIID = _transcript_ntiid( room, self.creator, self._NTIID_TYPE_ )
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
