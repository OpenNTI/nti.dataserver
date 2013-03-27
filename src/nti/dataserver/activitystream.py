#!/usr/bin/env python
"""
Functions and architecture for general activity streams.
$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)
from ZODB.loglevels import TRACE

from zope import component

from nti.dataserver import interfaces as nti_interfaces
from zope.lifecycleevent import IObjectModifiedEvent
import zope.intid.interfaces

from nti.intid.interfaces import IntIdMissingError

from .activitystream_change import Change

def enqueue_change( change, **kwargs ):
	ds = component.queryUtility( nti_interfaces.IDataserver )
	if ds:
		logger.log( TRACE, "Sending %s change to %s", change, kwargs )
		ds.enqueue_change( change, **kwargs )

def _enqueue_change_to_target( target, change, accum=None ):
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
	accum.add( target_key )

	# Fire the change off to the user using different threads.
	enqueue_change( change, target=target )

	for nested_entity in nti_interfaces.IEnumerableEntityContainer(target, ()):
		# Make this work for DynamicFriendsLists.
		# NOTE: Because of _get_dynamic_sharing_targets_for_read, there might actually
		# be duplicate change objects that get eliminated at read time.
		# But this ensures that the stream gets an object, bumps the notification
		# count, and sends a real-time notice to connected sockets.
		# TODO: Can we make it be just the later? Or remove _get_dynamic_sharing_targets_for_read?
		_enqueue_change_to_target( nested_entity, change, accum=accum )

# TODO: These listeners should probably be registered on something
# higher, like IModeledContent?

def _stream_preflight( contained ):
	if not nti_interfaces.IEntity.providedBy( getattr( contained, 'creator', None ) ):
		return None
	try:
		return getattr( contained, 'sharingTargets' )
	except AttributeError:
		return None

@component.adapter(nti_interfaces.IContained, zope.intid.interfaces.IIntIdRemovedEvent)
def stream_willRemoveIntIdForContainedObject( contained, event ):
	# Make the containing owner broadcast the stream DELETED event /now/,
	# while we can still get an ID, to keep catalogs and whatnot
	# up-to-date.
	deletion_targets = _stream_preflight( contained )
	if deletion_targets is None:
		return

	# First a broadcast
	event = Change( Change.DELETED, contained )
	event.creator = contained.creator
	enqueue_change( event, broadcast=True, target=contained.creator )
	# Then targeted
	accum = set()
	for target in deletion_targets:
		_enqueue_change_to_target( target, event, accum )

@component.adapter(nti_interfaces.IContained, zope.intid.interfaces.IIntIdAddedEvent)
def stream_didAddIntIdForContainedObject( contained, event ):
	creation_targets = _stream_preflight( contained )
	if creation_targets is None:
		return

	# First a broadcast
	event = Change( Change.CREATED, contained )
	event.creator = contained.creator
	enqueue_change( event, broadcast=True, target=contained.creator )
	# Then targeted
	accum = set()
	for target in creation_targets:
		_enqueue_change_to_target( target, event, accum )

@component.adapter(nti_interfaces.IContained, IObjectModifiedEvent)
def stream_didModifyObject( contained, event ):
	current_sharing_targets = _stream_preflight( contained )
	if current_sharing_targets is None:
		return

	if nti_interfaces.IObjectSharingModifiedEvent.providedBy( event ):
		_stream_enqeue_modification( contained.creator, Change.MODIFIED, contained, current_sharing_targets, event.oldSharingTargets)
	else:
		_stream_enqeue_modification( contained.creator, Change.MODIFIED, contained, current_sharing_targets )

def _stream_enqeue_modification( self, changeType, obj, current_sharing_targets, origSharing=None ):
	assert changeType == Change.MODIFIED

	current_sharing_targets = set(current_sharing_targets)
	if origSharing is None:
		origSharing = set(current_sharing_targets)

	# Step one is to announce all data changes globally as a broadcast.
	try:
		change = Change( changeType, obj )
	except IntIdMissingError:
		# No? In this case, we were trying to get a weak ref to the object,
		# but it has since been deleted and so further modifications are
		# pointless.
		# NOTE: This will go away
		logger.exception( "Not sending any changes for deleted object %r", obj )
		return
	change.creator = self
	enqueue_change( change, broadcast=True, target=self )

	newSharing = set(current_sharing_targets)
	seenTargets = set()


	if origSharing != newSharing:
		# OK, the sharing changed and its not a new or dead
		# object. People that it used to be shared with will get a
		# DELETE notice (if it is no longer indirectly shared with them at all; if it is, just
		# a MODIFIED notice). People that it is now shared with will
		# get a SHARED notice--these people should not later get
		# a MODIFIED notice for this action.
		deleteChange = Change( Change.DELETED, obj )
		deleteChange.creator = self
		createChange = Change( Change.SHARED, obj )
		createChange.creator = self
		for shunnedPerson in origSharing - newSharing:
			if obj.isSharedWith( shunnedPerson ):
				# Shared with him indirectly, not directly. We need to be sure
				# this stuff gets cleared from his caches, thus the delete notice.
				# but we don't want this to leave us because to the outside world it
				# is still shared. (Notice we also do NOT send a modified event to this user:
				# we dont want to put this data back into his caches.)
				deleteChange.send_change_notice = False
			else:
				deleteChange.send_change_notice = True # TODO: mutating this isn't really right, it is a shared persisted object
			_enqueue_change_to_target( shunnedPerson, deleteChange, seenTargets )
		for lovedPerson in newSharing - origSharing:
			_enqueue_change_to_target( lovedPerson, createChange, seenTargets )
			newSharing.remove( lovedPerson ) # Don't send MODIFIED, send SHARED

	# Deleted events won't change the sharing, so there's
	# no need to look for a union of old and new to send
	# the delete to.

	# Now broadcast the change to anyone that's left.
	for lovedPerson in newSharing:
		_enqueue_change_to_target( lovedPerson, change, seenTargets )
