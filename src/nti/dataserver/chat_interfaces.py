#!/usr/bin/env python2.7
"""Interfaces having to do with chat."""

from zope.interface import Interface

class IMeetingContainer(Interface):

	def create_meeting_from_dict( chatserver, meeting_dict, constructor ):
		"""
		Called to create (or return) a meeting instance within this container.
		:param chatserver: The chatserver.
		:param Mapping meeting_dict: The description of the room. You may modify
			this. If it has an 'Occupants' key, it will be an iterable of usernames or
			(username, sid) tuples.
		"""


	def meeting_became_empty( chatserver, meeting ):
		"""
		Called to notify that all occupants have left the meeting. The
		meeting will be declared inactive and deleted from
		the chatserver. It may be reactivated by this method, in which case
		it will not be deleted from the chatserver.
		"""


	def enter_active_meeting( chatserver, meeting_dict ):
		"""
		Called when someone wants to enter an active room (if there is one).
		:param meeting_dict: Guaranteed to have at least the Creator.
			May be modified. If this method fails, we will call :meth:create_meeting_from_dict
			with this same dictionary.
		:return: The active room, if successfully entered, otherwise None.
		"""


class IMeetingStorage(Interface):
	"""
	An object for the temporary shared storage of meetings
	that are active.
	"""

	def get(room_id):
		"""
		Returns the stored room having the given ID, or None
		if there is no room with that Id stored in this object.
		"""

	def __getitem__(room_id):
		"""
		Returns the stored room with that ID or raises KeyError.
		"""

	def add_room(room):
		"""
		Stores a room in this object. Sets the room's (an IContained)
		`id` property to be in the form produced by :func:`datatstructures.to_external_ntiid_oid`.
		"""

	def __delitem__(room_id):
		"""
		Removes the room stored in this object with the given id or
		raises KeyError.
		"""

class IUserTranscriptStorage(Interface):
	"""
	An object that knows how to store transcripts for users
	in a meeting.
	"""

	def transcript_for_meeting( meeting_id ): pass

	def add_message( meeting, msg ): pass
