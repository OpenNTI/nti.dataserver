#!/usr/bin/env python
"""
$Id$
"""

from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.ntiids import ntiids
from nti.dataserver import authorization
from nti.dataserver import authorization_acl as auth_acl
from zope.annotation import interfaces as ant_interfaces

@interface.implementer( chat_interfaces.IMeetingContainer )
class _AbstractMeetingContainerAdapter(object):

	ACTIVE_ROOM_ATTR = __name__ + '.' + '_mr_active_room'

	def __init__( self, container ):
		self.container = container

	def _has_active_meeting( self ):
		"""
		:return: An active meeting, or None.
		"""
		active_meeting = ant_interfaces.IAnnotations(  self.container ).get( self.ACTIVE_ROOM_ATTR, None )
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
		active_meeting = self._has_active_meeting()
		if active_meeting:
			logger.debug( "Not creating new meeting due to active meeting %s", active_meeting )
			# veto creation
			return None
		if meeting_dict.get('Creator') not in self._allowed_creators:
			logger.debug( "Not creating new meeting by unauthorized creator %s/%s",
						  meeting_dict.get( 'Creator'),
						  self._allowed_creators )
			return None

		occupants = self._allowed_occupants
		# save the original values so we can use the right tuple if needed.
		orig_occupants = { (x[0] if isinstance( x, tuple ) else x): x for x in meeting_dict['Occupants'] }

		occupants = [ (o if o not in orig_occupants else orig_occupants[o]) for o in occupants ]
		meeting_dict['Occupants'] = occupants

		result = constructor()
		ant_interfaces.IAnnotations( self.container )[self.ACTIVE_ROOM_ATTR] = result

		result.__parent__ = self.container
		# Apply an ACL allowing some to moderate
		# FIXME: XXX: This is overriding the IACLProvider registered for meetings.
		# We should probably implement this by making the object implement a new derived interface
		# and registering a provider for that

		aces = [auth_acl.ace_allowing( c, chat_interfaces.ACT_MODERATE, type(self)) for c in self._allowed_creators]

		# We cannot simply use the IACLProvider to get the rest of the permissions, because
		# the object is not configured yet, so for now we simply match its policy
		aces.extend( [auth_acl.ace_allowing( c, authorization.ACT_READ, type(self)) for c in self._allowed_creators.union( self._allowed_occupants )] )

		result.__acl__ = auth_acl.acl_from_aces( aces )

		return result


	def create_or_enter_meeting( self, chatserver, meeting_dict, constructor ):
		"""
		The combination of :meth:`create_or_enter_meeting` with :meth:`enter_active_meeting`.
		If an active meeting exists and the ``Creator`` is allowed to occupy it,
		then it will be returned. Otherwise, if the ``Creator`` is allowed to create
		one then it will be returned.
		:return: A tuple (meeting or None, created). If the first param is not None, the second
			param will say whether it was already active (False) or freshly created (True).
		"""
		active = self.enter_active_meeting( chatserver, meeting_dict )
		if active:
			return (active,False)
		return (self.create_meeting_from_dict( chatserver, meeting_dict, constructor ), True)

	def meeting_became_empty( self, chatserver, meeting ):
		try:
			del ant_interfaces.IAnnotations(self.container)[self.ACTIVE_ROOM_ATTR]
		except KeyError:
			pass

@component.adapter( nti_interfaces.IFriendsList )
class _FriendsListAdapter(_AbstractMeetingContainerAdapter):

	def __init__( self, friends_list ):
		super(_FriendsListAdapter, self).__init__( friends_list )

	@property
	def friends_list(self):
		return self.container

	@property
	def _allowed_creators(self):
		result = set( (self.friends_list.creator.username,) )
		return result

	@property
	def _allowed_occupants( self ):
		""" A set of the names of users that can be in the meeting. """
		occupants = { x.username for x in self.friends_list }
		occupants.add( self.friends_list.creator.username )
		return occupants

	def enter_active_meeting( self, chatserver, meeting_dict ):
		"""
		Any time the creator wants to re-enter the room, if people
		have left then we start fresh...in fact, we always start
		fresh, in order to send out 'entered room' messages. This is
		poorly done and can lead to 'DOS' for the poor friends
		"""
		active_meeting = super(_FriendsListAdapter,self).enter_active_meeting( chatserver, meeting_dict )
		if active_meeting and meeting_dict.get( 'Creator' ) == self.friends_list.creator.username:
			logger.debug( "Recreating friends list room for creator %s (due to missing people %s != %s?)",
						  meeting_dict.get( 'Creator' ), active_meeting.occupant_names, self._allowed_occupants )
			self.meeting_became_empty( chatserver, active_meeting )
			active_meeting = None

		return active_meeting

@component.adapter( nti_interfaces.ISectionInfo )
class _ClassSectionAdapter(_AbstractMeetingContainerAdapter):

	def __init__( self, section ):
		super(_ClassSectionAdapter,self).__init__( section )

	@property
	def _allowed_occupants( self ):
		occupants = set( self.container.Enrolled )
		occupants = occupants | set( self.container.InstructorInfo.Instructors )
		return occupants

	@property
	def _allowed_creators( self ):
		return set(self.container.InstructorInfo.Instructors)

	def enter_active_meeting( self, chatserver, meeting_dict ):
		"""
		If the creator of a class section (an instructor) re-enters it,
		then all students are automatically re-added, whether or not
		they had left. The same room and session are used for transcript purposes,
		but we broadcast enter-room events to everyone.e This is to address some reliability
		concerns.
		"""
		active_meeting = super(_ClassSectionAdapter,self).enter_active_meeting( chatserver, meeting_dict )
		if active_meeting and meeting_dict.get( 'Creator' ) in self._allowed_creators:
			logger.debug( "Rebroadcasting class section room for creator %s (due to missing people %s != %s?)",
						  meeting_dict.get( 'Creator' ), active_meeting.occupant_names, self._allowed_occupants )
			# First, silently add everyone to the room
			active_meeting.add_occupant_names( self._allowed_occupants, broadcast=False )
			# Now, to everyone, even the creator (who may or may not get his own event) broadcast
			# that they're in the room and that the room membership has changed
			event_to =  self._allowed_occupants
			active_meeting.emit_enteredRoom( event_to, active_meeting )
			active_meeting.emit_roomMembershipChanged( event_to, active_meeting )


		return active_meeting

class MeetingContainerStorage(object):
	"""
	An object that implements meeting container storage
	for the chatserver.
	"""

	def __init__( self, server=None ):
		"""
		:param server: If given and not None, the dataserver used to lookup entities.
			If not given, the global default will be used.
		"""
		self.server = server

	def get( self, container_id, default=None ):
		result = None
		provider = ntiids.get_provider( container_id )
		if provider and ntiids.is_ntiid_of_type( container_id, ntiids.TYPE_MEETINGROOM ):
			container = ntiids.find_object_with_ntiid( container_id )
			result = component.queryAdapter( container, chat_interfaces.IMeetingContainer )

		return result or default
