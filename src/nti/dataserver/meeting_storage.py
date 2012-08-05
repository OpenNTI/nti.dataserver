#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dataserver-specific storage for :mod:`nti.chatserver` :class:`nti.chatserver.meeting._Meeting`.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import

from zope import interface
from zope import component
import zope.annotation

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from ZODB.interfaces import IConnection

from nti.externalization import oids
from nti.ntiids import ntiids
from nti.dataserver import users
from nti.dataserver.datastructures import check_contained_object_for_storage
from nti.dataserver.containers import LastModifiedBTreeContainer

class IMeetingContainer(zope.container.interfaces.IBTreeContainer): pass

@interface.implementer(IMeetingContainer)
@component.adapter(nti_interfaces.IEntity)
class _MeetingContainer(LastModifiedBTreeContainer): # TODO: Container constraints
	pass

EntityMeetingContainerAnnotation = zope.annotation.factory(_MeetingContainer)

@interface.implementer(chat_interfaces.IMeetingStorage)
class CreatorBasedAnnotationMeetingStorage(object):
	"""
	An implementation of :class:`chat_interfaces.IMeetingStorage` that
	looks up creators and stores the meeting on the creator using a
	:class:`zope.container.interfaces.IContainer`, similar to how
	a :class:`nti.dataserver.datastructures.ContainedStorage` works. Like with that class,
	meetings are assigned ID values based on their OID NTIID. (It would be nice
	to somehow work in the intid value, but we don't have that.)


	"""

	def __init__( self ):
		pass

	def __delitem__( self, room_id ):
		"""
		Rooms cannot be deleted using this storage. They accumulate on the user
		until such time as we decide to manually clean them out or the
		user goes away.
		"""
		pass # pragma: no cover

	def __getitem__( self, room_id ):
		result =  self.get( room_id )
		if result is None: # pragma: no cover
			raise KeyError( room_id ) # compat with mapping contract
		return result

	def get( self, room_id ):
		return ntiids.find_object_with_ntiid( room_id )

	def add_room( self, room ):
		check_contained_object_for_storage( room )
		creator_name = room.creator
		creator = users.Entity.get_entity( creator_name )

		meeting_container = IMeetingContainer(creator)

		# Ensure that we can get an NTIID
		if IConnection( room, None ) is None:
			IConnection( creator ).add( room )

		room.id = oids.to_external_ntiid_oid( room, None )

		meeting_container[room.id] = room

@interface.implementer(chat_interfaces.IMessageInfoStorage)
@component.adapter(nti_interfaces.IEntity)
class _MessageInfoContainer(LastModifiedBTreeContainer): # TODO: Container constraints
	"""
	Messages have IDs that are UUIDs, so we use that as the key
	in the container.
	TODO: Can we be more efficient?
	"""

	def add_message( self, msg_info ):
		self[msg_info.ID] = msg_info

EntityMessageInfoContainerAnnotation = zope.annotation.factory(_MessageInfoContainer)


@interface.implementer(chat_interfaces.IMessageInfoStorage)
@component.adapter(chat_interfaces.IMessageInfo)
def CreatorBasedAnnotationMessageInfoStorage( msg_info ):
	"""
	A factory for finding message storages for the given message, based
	on the creator of the message.

	We basically do a double-dispatch here. The meeting room finds this object
	based on the IMessageInfo, and then we find the actual storage based
	on the creator of the message.
	"""

	check_contained_object_for_storage( msg_info )
	creator_name = msg_info.creator
	creator = users.Entity.get_entity( creator_name )
	__traceback_info__ = creator, creator_name, msg_info

	message_container = chat_interfaces.IMessageInfoStorage( creator )
	return message_container
