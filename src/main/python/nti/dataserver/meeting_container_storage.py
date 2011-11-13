#!/usr/bin/env python2.7

from zope import component
from zope import interface

from . import users
from . import chat
from . import ntiids
from . import classes

class _AbstractMeetingContainerAdapter(object):
	interface.implements( chat.IMeetingContainer )

	ACTIVE_ROOM_ATTR = '_mr_active_room'

	def __init__( self, container ):
		self.container = container

	def _has_active_meeting( self ):
		"""
		:return: An active meeting, or None.
		"""
		active_meeting = getattr( self.container, self.ACTIVE_ROOM_ATTR, None )
		if active_meeting and active_meeting.Active:
			return active_meeting
		return None

	@property
	def _allowed_occupants( self ):
		""" A set of the names of users that can be in the meeting. """
		raise NotImplementedError()

	@property
	def _allowed_creators( self ):
		""" A set of people that can create a room. """
		return self._allowed_occupants

	def enter_active_meeting( self, chatserver, meeting_dict ):
		# If there is an active meeting, and I'm on the allowed list,
		# then let me join. Woot woot.
		active_meeting = self._has_active_meeting( )
		result = None
		if active_meeting:
			if meeting_dict.get( 'Creator' ) in self._allowed_occupants:
				result = active_meeting

		# Snarkers. Either there was no meeting, or the Creator is not
		# invited. Therefore, deny. Note that there's no state we need to
		# preserve: these same checks are performed in create_meeting
		return result

	def create_meeting_from_dict( self, chatserver, meeting_dict, constructor ):
		if self._has_active_meeting():
			# veto creation
			return None
		if meeting_dict.get('Creator') not in self._allowed_creators:
			return None

		occupants = self._allowed_occupants
		# save the original values so we can use the right tuple if needed.
		orig_occupants = { (x[0] if isinstance( x, tuple ) else x): x for x in meeting_dict['Occupants'] }

		occupants = [ (o if o not in orig_occupants else orig_occupants[o]) for o in occupants ]
		meeting_dict['Occupants'] = occupants

		result = constructor()
		setattr( self.container, self.ACTIVE_ROOM_ATTR, result )
		return result

	def meeting_became_empty( self, chatserver, meeting ):
		try:
			delattr( self.container, self.ACTIVE_ROOM_ATTR )
		except AttributeError:
			pass

class _FriendsListAdapter(_AbstractMeetingContainerAdapter):
	component.adapts( users.FriendsList )

	def __init__( self, friends_list ):
		super(_FriendsListAdapter, self).__init__( friends_list )

	@property
	def friends_list(self):
		return self.container

	@property
	def _allowed_occupants( self ):
		""" A set of the names of users that can be in the meeting. """
		occupants = { x.username for x in self.friends_list }
		occupants.add( self.friends_list.creator.username )
		return occupants

class _ClassSectionAdapter(_AbstractMeetingContainerAdapter):
	component.adapts( classes.SectionInfo )

	def __init__( self, section ):
		super(_ClassSectionAdapter,self).__init__( section )

	@property
	def _allowed_occupants( self ):
		occupants = set( self.container.Enrolled )
		occupants = occupants | set( self.container.InstructorInfo.Instructors )
		return occupants

	@property
	def _allowed_creators( self ):
		return self.container.InstructorInfo.Instructors


class MeetingContainerStorage(object):
	"""
	An object that implements meeting container storage
	for the chatserver.
	"""

	def __init__( self, server ):
		self.server = server

	def get_by_ntiid( self, container_id ):
		"""
		Make us look like an Entity for our purposes to avoid None handling.
		"""
		return None

	def get( self, container_id, default=None ):
		result = None
		provider = ntiids.get_provider( container_id )
		if provider and ntiids.is_ntiid_of_type( container_id, ntiids.TYPE_MEETINGROOM ):
			# TODO: Providers and users are in two different namespaces.
			# We're only distinguishing that now by the presence or absence of a @ in their
			# name. What's right?
			entity = users.Entity.get_entity( provider, self.server, default=self,
											  _namespace=('users' if '@' in provider else 'providers') )
			container = entity.get_by_ntiid( container_id )
			result = component.queryAdapter( container, chat.IMeetingContainer )

		return result or default

