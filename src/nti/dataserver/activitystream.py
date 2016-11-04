#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions and architecture for general activity streams.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.event import notify

from zope.lifecycleevent import IObjectModifiedEvent

from zope.security.management import queryInteraction

from nti.dataserver.activitystream_change import Change

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IContained
from nti.dataserver.interfaces import TargetedStreamChangeEvent
from nti.dataserver.interfaces import IObjectSharingModifiedEvent
from nti.dataserver.interfaces import ISharingTargetEntityIterable

from nti.intid.interfaces import IIntIdAddedEvent
from nti.intid.interfaces import IntIdMissingError
from nti.intid.interfaces import IIntIdRemovedEvent

def _enqueue_change_to_target(target, change, accum=None):
	"""
	Enqueue the ``change`` to the ``target``. If the ``target`` can be iterated
	across to expand into additional targets, this method will recurse
	to send the event to those additional targets.

	This method ensures that each leaf target only gets one change of a given type
	(within the given ``accum`` state).

	This method ensures that the change is not directed to the creator
	of the change.

	:param accum: A set used to hold recursion state.
	"""

	if target is None or change is None or target is change.creator:
		return

	accum = set() if accum is None else accum

	target_key = (target, change.type)
	if target_key in accum:
		return
	accum.add(target_key)

	# Fire the change off to the user
	notify(TargetedStreamChangeEvent(change, target))

	# Make this work for DynamicFriendsLists.
	# NOTE: We could now make it work for communities too, since
	# we now have an implementation of that interface. However, that's
	# different than what we were doing before, and probably inefficient,
	# and probably needs some normalization.
	for nested_entity in ISharingTargetEntityIterable(target, ()):
		# NOTE: Because of _get_dynamic_sharing_targets_for_read, there might actually
		# be duplicate change objects that get eliminated at read time.
		# But this ensures that the stream gets an object, bumps the notification
		# count, and sends a real-time notice to connected sockets.
		# TODO: Can we make it be just the later?
		# Or remove _get_dynamic_sharing_targets_for_read?
		_enqueue_change_to_target(nested_entity, change, accum=accum)

# TODO: These listeners should probably be registered on something
# higher, like IModeledContent?
# Note that we are registered on the versions that are guaranteed to fire
# around Zope catalogs having been updated so that we (and listeners to what
# we fire) can make use of them.

def hasQueryInteraction():
	return queryInteraction() is not None

def _stream_preflight(contained):
	# Make sure we don't broadcast changes for system created
	# objects or when interaction is disabled.
	if (	not IEntity.providedBy(getattr(contained, 'creator', None))
		or	not hasQueryInteraction() ):
		return None
	try:
		return getattr(contained, 'sharingTargets')
	except AttributeError:
		return None

@component.adapter(IContained, IIntIdRemovedEvent)
def stream_willRemoveIntIdForContainedObject(contained, event):
	# Make the containing owner broadcast the stream DELETED event /now/,
	# while we can still get an ID, to keep catalogs and whatnot
	# up-to-date.
	deletion_targets = _stream_preflight(contained)
	if deletion_targets is None:
		return

	event = Change(Change.DELETED, contained)
	event.creator = contained.creator

	# Then targeted
	accum = set()
	for target in deletion_targets or ():
		_enqueue_change_to_target(target, event, accum)

@component.adapter(IContained, IIntIdAddedEvent)
def stream_didAddIntIdForContainedObject(contained, event):
	creation_targets = _stream_preflight(contained)
	if creation_targets is None:
		return

	event = Change(Change.CREATED, contained)
	event.creator = contained.creator

	# Then targeted
	accum = set()
	for target in creation_targets:
		_enqueue_change_to_target(target, event, accum)

from zope.container.interfaces import IContainerModifiedEvent

from nti.dataserver.interfaces import INotModifiedInStreamWhenContainerModified

@component.adapter(IContained, IObjectModifiedEvent)
def stream_didModifyObject(contained, event):
	if (IContainerModifiedEvent.providedBy(event)
		and INotModifiedInStreamWhenContainerModified.providedBy(contained)):
		# Bypass. See INotModifiedInStreamWhenContainerModified for rationale
		return

	current_sharing_targets = _stream_preflight(contained)
	if current_sharing_targets is None:
		return

	if IObjectSharingModifiedEvent.providedBy(event):
		_stream_enqeue_modification(contained.creator,
									Change.MODIFIED,
									contained,
									current_sharing_targets,
									event.oldSharingTargets)
	else:
		_stream_enqeue_modification(contained.creator,
									Change.MODIFIED,
									contained,
									current_sharing_targets)

def _stream_enqeue_modification(self, changeType, obj, current_sharing_targets,
								origSharing=None):

	assert changeType == Change.MODIFIED

	current_sharing_targets = set(current_sharing_targets)
	if origSharing is None:
		origSharing = set(current_sharing_targets)

	try:
		change = Change(changeType, obj)
	except IntIdMissingError:
		# No? In this case, we were trying to get a weak ref to the object,
		# but it has since been deleted and so further modifications are
		# pointless.
		# NOTE: This will go away
		logger.error("Not sending any changes for deleted object %r", obj)
		return
	change.creator = self

	newSharing = set(current_sharing_targets)
	seenTargets = set()

	if origSharing != newSharing:
		# OK, the sharing changed and its not a new or dead
		# object. People that it used to be shared with will get a
		# DELETE notice (if it is no longer indirectly shared with them at all;
		# if it is, just a MODIFIED notice). People that it is now shared with will
		# get a SHARED notice--these people should not later get
		# a MODIFIED notice for this action.
		deleteChange = Change(Change.DELETED, obj)
		deleteChange.creator = self
		sharedChange = Change(Change.SHARED, obj)
		sharedChange.creator = self
		for shunnedPerson in origSharing - newSharing:
			if obj.isSharedWith(shunnedPerson):
				# Shared with him indirectly, not directly. We need to be sure
				# this stuff gets cleared from his caches, thus the delete notice.
				# but we don't want this to leave us because to the outside world it
				# is still shared. (Notice we also do NOT send a modified event
				# to this user: we dont want to put this data back into his caches.)
				deleteChange.send_change_notice = False
			else:
				# TODO: mutating this isn't really right, it is a shared persisted object
				deleteChange.send_change_notice = True
			_enqueue_change_to_target(shunnedPerson, deleteChange, seenTargets)
		for lovedPerson in newSharing - origSharing:
			_enqueue_change_to_target(lovedPerson, sharedChange, seenTargets)
			newSharing.remove(lovedPerson)  # Don't send MODIFIED, send SHARED

	# Deleted events won't change the sharing, so there's
	# no need to look for a union of old and new to send
	# the delete to.

	# Now broadcast the change to anyone that's left.
	for lovedPerson in newSharing:
		_enqueue_change_to_target(lovedPerson, change, seenTargets)
