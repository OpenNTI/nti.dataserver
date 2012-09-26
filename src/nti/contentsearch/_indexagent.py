#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import six

from zope import component
from ZODB import loglevels

from nti.dataserver.activitystream_change import Change

from nti.contentsearch import get_indexable_types
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger(__name__)

_event_types = { Change.CREATED: 'index_user_content',
				 Change.SHARED:  'index_user_content',
				 Change.MODIFIED:'update_user_content',
				 Change.DELETED: 'delete_user_content' }

_only_delete_by_owner = False

def get_creator(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_creator() if adapted else None
							
def _check_event(target, change_type, data_type, data):
	result = change_type in _event_types and normalize_type_name(data_type) in get_indexable_types()
	if result and _only_delete_by_owner and change_type==Change.DELETED:
		username = target if isinstance( target, six.string_types ) else target.username
		creator = get_creator(data)
		result = username == creator
	return result

def _process_event(indexmanager, target, change_type, data_type, data):
	if 	_check_event(target, change_type, data_type, data):

		logger.log( loglevels.BLATHER, 'Index event ("%s", "%s", "%s") received', target, change_type, data_type)

		func_name = _event_types.get( change_type )
		func = getattr( indexmanager, func_name, None ) if func_name else None
		return func( target, data=data, type_name=data_type ) or True if func else False

	return False

def handle_index_event(indexmanager, target, msg):
	if indexmanager and target and msg:
		obj = getattr(msg, "object", None)
		if obj:
			return _process_event(indexmanager, target, msg.type, obj.__class__.__name__, obj)

	return False
