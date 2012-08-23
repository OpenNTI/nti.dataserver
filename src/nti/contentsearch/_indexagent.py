#!/usr/bin/env python

from __future__ import print_function, unicode_literals

from ZODB import loglevels

from nti.dataserver.activitystream_change import Change

from nti.contentsearch import get_indexable_types
from nti.contentsearch.common import normalize_type_name


import logging
logger = logging.getLogger(__name__)

_event_types = { Change.CREATED: 'index_user_content',
				 Change.SHARED:  'index_user_content',
				 Change.MODIFIED:'update_user_content',
				 Change.DELETED: 'delete_user_content' }

def _process_event(indexmanager, target, change_type, data_type, data):
	if 	change_type in _event_types and normalize_type_name(data_type) in get_indexable_types():

		logger.log( loglevels.TRACE, 'Index event ("%s", "%s", "%s") received', target, change_type, data_type)

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
