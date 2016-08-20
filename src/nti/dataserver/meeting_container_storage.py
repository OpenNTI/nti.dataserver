#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.chatserver.interfaces import ACT_MODERATE
from nti.chatserver.interfaces import IMeetingContainer

from nti.dataserver import authorization
from nti.dataserver import authorization_acl as auth_acl

from nti.dataserver.interfaces import IFriendsList

from nti.ntiids import ntiids

from nti.property.property import alias
from nti.property.property import annotation_alias

@interface.implementer(IMeetingContainer)
class _AbstractMeetingContainerAdapter(object):
	"""
	Common base class for persistent meeting container
	adapter implementations (:class:`nti.chatserver.interfaces.IMeetingContainer`).


	Subclasses *must* define :attr:`_allowed_occupants` and *may* define
	:attr:`_allowed_creators`
	(if they don't it is the same as :attr:`_allowed_occupants`).

	This object defines the following attributes:

	.. py:attribute:: context

		The context object. The context object *must* be adaptable to
		:class:`zope.annotation.interfaces.IAnnotations`.
	"""

	#: The name of the annotation we use to store an active room on the context object.
	ACTIVE_ROOM_ATTR = __name__ + '.' + '_mr_active_room'

	def __init__(self, container):
		self.context = container

	container = alias('context')
	_active_meeting = annotation_alias(ACTIVE_ROOM_ATTR,
									   annotation_property='context',
									   delete=True)

	def _has_active_meeting(self):
		"""
		:return: An active meeting, or None.
		"""
		# ant_interfaces.IAnnotations( self.context ).get( self.ACTIVE_ROOM_ATTR, None )
		active_meeting = self._active_meeting
		if active_meeting and active_meeting.Active:
			return active_meeting
		return None

	@property
	def _allowed_occupants(self):
		""" 
		A set of the names of users that can be in the meeting.
		"""
		raise NotImplementedError()  # pragma: no cover

	@property
	def _allowed_creators(self):
		""" 
		A set of usernames that can create a room.
		"""
		return self._allowed_occupants  # pragma: no cover

	def enter_active_meeting(self, chatserver, meeting_dict):
		# If there is an active meeting, and I'm on the allowed list,
		# then let me join. Woot woot.
		active_meeting = self._has_active_meeting()
		result = None
		if active_meeting:
			if meeting_dict.get('Creator') in self._allowed_occupants:
				result = active_meeting

		# Snarkers. Either there was no meeting, or the Creator is not
		# invited. Therefore, deny. Note that there's no state we need to
		# preserve: these same checks are performed in create_meeting
		return result

	def create_meeting_from_dict(self, chatserver, meeting_dict, constructor):
		active_meeting = self._has_active_meeting()
		if active_meeting:
			logger.debug("Not creating new meeting due to active meeting %s", active_meeting)
			# veto creation
			return None
		if meeting_dict.get('Creator') not in self._allowed_creators:
			logger.debug("Not creating new meeting by unauthorized creator %s/%s",
						 meeting_dict.get('Creator'),
						 self._allowed_creators)
			return None

		occupants = self._allowed_occupants
		# save the original values so we can use the right tuple if needed.
		orig_occupants = { (x[0] if isinstance(x, tuple) else x): x for x in meeting_dict['Occupants'] }

		occupants = [ (o if o not in orig_occupants else orig_occupants[o]) for o in occupants ]
		meeting_dict['Occupants'] = occupants

		result = constructor()
		self._active_meeting = result  # ant_interfaces.IAnnotations( self.context )[self.ACTIVE_ROOM_ATTR] = result

		result.__parent__ = self.context
		# Apply an ACL allowing some to moderate
		# FIXME: XXX: This is overriding the IACLProvider registered for meetings.
		# We should probably implement this by making the object implement a new derived interface
		# and registering a provider for that

		aces = [auth_acl.ace_allowing(c, ACT_MODERATE, type(self))
				for c in self._allowed_creators]

		# We cannot simply use the IACLProvider to get the rest of the permissions, because
		# the object is not configured yet, so for now we simply match its policy
		aces.extend([auth_acl.ace_allowing(c, authorization.ACT_READ, type(self))
					 for c in self._allowed_creators.union(self._allowed_occupants)])

		result.__acl__ = auth_acl.acl_from_aces(aces)
		return result

	def create_or_enter_meeting(self, chatserver, meeting_dict, constructor):
		"""
		The combination of :meth:`create_or_enter_meeting` with :meth:`enter_active_meeting`.
		If an active meeting exists and the ``Creator`` is allowed to occupy it,
		then it will be returned. Otherwise, if the ``Creator`` is allowed to create
		one then it will be returned.

		:return: A tuple (meeting or None, created). If the first param is not None, the second
			param will say whether it was already active (False) or freshly created (True).
		"""
		active = self.enter_active_meeting(chatserver, meeting_dict)
		if active:
			return (active, False)
		return (self.create_meeting_from_dict(chatserver, meeting_dict, constructor), True)

	def meeting_became_empty(self, chatserver, meeting):
		del self._active_meeting

@component.adapter(IFriendsList)
class _FriendsListAdapter(_AbstractMeetingContainerAdapter):
	"""
	Implements the policy to allow a :class:`nti.dataserver.interfaces.IFriendsList` to
	be used as a meeting container.
	"""

	def __init__(self, friends_list):
		super(_FriendsListAdapter, self).__init__(friends_list)

	friends_list = alias('context')

	@property
	def _allowed_creators(self):
		"""
		Only the owner (creator) of a FriendsList is allow to initiate
		a new room.

		:return: A fresh :class:`set` of usernames.
		"""

		return {self.context.creator.username}

	@property
	def _allowed_occupants(self):
		"""
		The owner (creator) and all members of the FriendsList are allowed to be occupants
		of the room..

		:return: A fresh :class:`set` of usernames.
		"""
		occupants = { x.username for x in self.context }
		occupants.add(self.friends_list.creator.username)
		return occupants

	def enter_active_meeting(self, chatserver, meeting_dict):
		"""
		Any time the creator wants to re-enter the room, if people
		have left then we start fresh...in fact, we always start
		fresh, in order to send out 'entered room' messages. This is
		poorly done and can lead to 'DOS' for the poor friends
		"""
		active_meeting = super(_FriendsListAdapter, self).enter_active_meeting(chatserver, meeting_dict)
		if active_meeting and meeting_dict.get('Creator') == self.friends_list.creator.username:
			logger.debug("Recreating friends list room for creator %s (due to missing people %s != %s?)",
						  meeting_dict.get('Creator'), active_meeting.occupant_names, self._allowed_occupants)
			self.meeting_became_empty(chatserver, active_meeting)
			active_meeting = None

		return active_meeting

class MeetingContainerStorage(object):
	"""
	An object that implements meeting container storage
	for the chatserver.
	"""

	def __init__(self, server=None):
		"""
		:param server: If given and not None, the dataserver used to lookup entities.
			If not given, the global default will be used.
		"""
		self.server = server

	def get(self, container_id, default=None):
		result = None
		provider = ntiids.get_provider(container_id)
		if provider and ntiids.is_ntiid_of_type(container_id, ntiids.TYPE_MEETINGROOM):
			container = ntiids.find_object_with_ntiid(container_id)
			result = component.queryAdapter(container, IMeetingContainer)
		return result or default
