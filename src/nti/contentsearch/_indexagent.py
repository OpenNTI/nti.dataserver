from __future__ import print_function, unicode_literals

import six

from zope import component
from ZODB import loglevels

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import Entity

from nti.contentsearch import get_indexable_types
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger(__name__)

_event_types = { nti_interfaces.SC_CREATED: 'index_user_content',
				 nti_interfaces.SC_SHARED:  'index_user_content',
				 nti_interfaces.SC_MODIFIED:'update_user_content',
				 nti_interfaces.SC_DELETED: 'delete_user_content' }

_only_delete_by_owner = True

def get_creator(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_creator()

def _check_event(target, change_type, data_type, data):
	result = change_type in _event_types and normalize_type_name(data_type) in get_indexable_types()
	if result and _only_delete_by_owner and change_type == nti_interfaces.SC_DELETED:
		username = target if isinstance( target, six.string_types ) else target.username
		creator = get_creator(data)
		result = username == creator
	return result

def _process_event(indexmanager, target, change_type, data_type, data):
	if 	_check_event(target, change_type, data_type, data):

		logger.log( loglevels.TRACE, 'Index event ("%s", "%s", "%s") received', target, change_type, data_type)

		func_name = _event_types.get( change_type )
		func = getattr( indexmanager, func_name, None ) if func_name else None
		return func( target, data=data, type_name=data_type ) or True if func else False

	return False

def handle_index_event(indexmanager, target, change, broadcast=None):
	"""
	Updates indexes according to the change being communicated. Indexes are
	only updated when the target entity directly owns or is directly shared with
	the changed object.

	:param target: An :class:`nti.dataserver.interfaces.IEntity` to which the event
		is directed. Higher levels are responsible for dispatching to all
		the individual targets effected, unwinding nesting, etc.

	:param change: An :class:`nti.dataserver.interfaces.IStreamChangeEvent` holding
		the object that that has changed.

	:param broadcast: This is set to true when events are being sent for the sole
		purpose of indexing to the target. In that case, we bypass any sharing/ownership
		restrictions and do process the event. NOTE: This is unfortunately tightly coupled with
		users.py and chat_transcripts.py and needs rethought. chat_transcripts.py sends all
		events as broadcasts

	"""
	if not indexmanager or not target or not change or change.object is None:
		return

	change_object = change.object
	should_process = True
	if not broadcast: # only check if we're not a global broadcast
		if change.type in (nti_interfaces.SC_CREATED, nti_interfaces.SC_SHARED, nti_interfaces.SC_MODIFIED):
			entity = target
			if isinstance( target, six.string_types ):
				entity = Entity.get_entity( target ) # FIXME: Tightly coupled
			should_process = change_object.isSharedDirectlyWith( entity )

	if should_process:
		return _process_event(indexmanager, target, change.type, change_object.__class__.__name__, change_object)

	return False
