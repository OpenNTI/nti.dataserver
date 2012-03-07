""" Chatserver functionality. """

import logging
logger = logging.getLogger( __name__ )

from nti.dataserver import ntiids
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import chat_interfaces
from nti.dataserver import mimetype
from nti.dataserver import users
from nti.dataserver import datastructures
from nti.dataserver import links

from persistent import Persistent
import BTrees.OOBTree

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

class _MeetingTranscriptStorage(Persistent,datastructures.ContainedMixin,datastructures.CreatedModDateTrackingObject):
	"""
	The storage for the transcript of a single session.
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
		# TODO: Use an IContainer
		self.meeting = meeting

	def add_message( self, msg ):
		self.messages[msg.ID] = msg

	def itervalues(self):
		return self.messages.itervalues()

def _transcript_ntiid( meeting, creator, nttype=ntiids.TYPE_TRANSCRIPT_SUMMARY ):
	"""
	:return: A NTIID string representing the transcript (summary) for the
		given meeting (chat session) with the given participant.
	"""
	return ntiids.make_ntiid( base=meeting.id,
							  date=meeting.CreatedTime,
							  provider=(creator.username if creator else None),
							  nttype=nttype )

class _UserTranscriptStorageAdapter(object):
	"""
	The storage for all of a user's transcripts.

	You can look up transcripts by meeting ID.

	"""

	interface.implements(chat_interfaces.IUserTranscriptStorage)
	component.adapts(users.User)

	def __init__( self, user ):
		self._user = user

	def transcript_for_meeting( self, meeting_id ):
		result = None
		# FIXME: The meeting is in a different db and not referenced
		# so is subject to GC. Once we have the user indexing
		# by contained NTIID, we can simply ask it after
		# deriving the storage_id
		meeting = component.queryUtility( nti_interfaces.IDataserver ).get_by_oid( meeting_id )
		if meeting is not None:
			storage_id = _transcript_ntiid( meeting, self._user )
			storage = self._user.getContainedObject( meeting.containerId, storage_id )
			result = Transcript( storage ) if storage else None
		else:
			logger.debug( "No meeting %s in %s", meeting_id, self._user )
		return result

	@property
	def transcript_summaries( self ):
		result = []
		for container in self._user.getAllContainers().values():
			if isinstance( container, float ): continue
			for storage in container.values():
				if isinstance(storage, _MeetingTranscriptStorage):
					result.append( TranscriptSummary( storage ) )
		return result

	def add_message( self, meeting, msg, ):
		assert msg.containerId
		assert msg.containerId == meeting.ID
		# Our transcript storage we store with the
		# provider ID of our user
		storage_id = _transcript_ntiid( meeting, self._user )
		room = self._user.getContainedObject( meeting.containerId, storage_id )
		if not room:
			room = _MeetingTranscriptStorage( meeting )
			room.id = storage_id
			room.containerId = meeting.containerId
			self._user.addContainedObject( room )

		room.add_message( msg )


class TranscriptSummary(datastructures.ExternalizableInstanceDict):
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
			self.LastModified = max( _messages, key=lambda m: m.LastModified ).LastModified
		else:
			# cannot max() empty sequence
			self.LastModified = 0

		self.Contributors = set()
		for msg in _messages:
			self.Contributors.update( msg.sharedWith or () )

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
		return None
