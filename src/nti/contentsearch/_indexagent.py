from nti.dataserver.users import Change
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import indexable_type_names

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

def _process_event(indexmanager, creator, change_type, data_type, data):
	if 	change_type in (Change.CREATED, Change.SHARED, Change.MODIFIED, Change.DELETED) and \
		normalize_type_name(data_type) in indexable_type_names:
		
		logger.debug('Index event ("%s", "%s", "%s",  %s) received' % (creator, change_type, data_type, data))
		
		if change_type in (Change.CREATED, Change.SHARED):
			indexmanager.index_user_content(data=data, username=creator, type_name=data_type)
		elif change_type == Change.MODIFIED:
			indexmanager.update_user_content(data=data, username=creator, type_name=data_type)
		elif Change.DELETED:
			indexmanager.delete_user_content(data=data, username=creator, type_name=data_type)
		
		return True
	
	return False
	
def handle_index_event(indexmanager, username, msg):
	if indexmanager and username and msg:
		obj = getattr(msg, "object", None)
		if obj:
			data = obj
			if callable( getattr( obj, 'toExternalObject', None ) ):
				data = obj.toExternalObject()
			return _process_event(indexmanager, username, msg.type, obj.__class__.__name__, data)

	return False
