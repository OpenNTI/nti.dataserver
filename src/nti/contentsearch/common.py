from __future__ import print_function, unicode_literals

import re
import six
import time
import collections
from time import mktime
from datetime import datetime

from nti.externalization import interfaces as ext_interfaces

from nti.mimetype.mimetype import MIME_BASE

import logging
logger = logging.getLogger( __name__ )


ID 				= unicode(ext_interfaces.StandardExternalFields.ID)
HIT 			= u'Hit'
OID 			= unicode(ext_interfaces.StandardExternalFields.OID)
TYPE 			= u'Type'
BODY			= u'Body'
INTID			= u'INTID'
NTIID 			= unicode(ext_interfaces.StandardExternalFields.NTIID)
CLASS 			= unicode(ext_interfaces.StandardExternalFields.CLASS)
QUERY 			= u'Query'
ITEMS			= u'Items'
CONTENT			= u'Content'
SNIPPET 		= u'Snippet'
CREATOR 		= unicode(ext_interfaces.StandardExternalFields.CREATOR)
AUTO_TAGS		= u'AutoTags'
MIME_TYPE		= unicode(ext_interfaces.StandardExternalFields.MIMETYPE)
HIT_COUNT 		= u'Hit Count'
TARGET_OID		= u'TargetOID'
MESSAGE_INFO	= u'MessageInfo'
SUGGESTIONS		= u'Suggestions'
CONTAINER_ID	= unicode(ext_interfaces.StandardExternalFields.CONTAINER_ID)
COLLECTION_ID	= u'CollectionId'
LAST_MODIFIED	= unicode(ext_interfaces.StandardExternalFields.LAST_MODIFIED)


id_				= unicode(ext_interfaces.StandardInternalFields.ID)
oid_			= u'oid'
body_ 			= u'body'
text_			= u'text'
type_			= u'type'
tags_			= u'tags'
quick_			= u'quick'
title_			= u'title'
intid_			= u'intid'
ntiid_			= unicode(ext_interfaces.StandardInternalFields.NTIID)
color_			= u'color'
p_oid_			= u'_p_oid'
title_			= u'title'
ngrams_			= u'ngrams'
channel_		= u'channel'
section_		= u'section'
username_		= u'username'
creator_		= unicode(ext_interfaces.StandardInternalFields.CREATOR)
related_		= u'related'
content_		= u'content'
keywords_		= u'keywords'
references_		= u'references'
inReplyTo_		= u'inReplyTo'
recipients_		= u'recipients'
sharedWith_		= u'sharedWith'
selectedText_ = u'selectedText'
containerId_	= unicode(ext_interfaces.StandardInternalFields.CONTAINER_ID)
collectionId_	= u'collectionId'
last_modified_	= u'last_modified'
replacementContent_ = u'replacementContent'
redactionExplanation_ = u'redactionExplanation'
flattenedSharingTargetNames_ = u'flattenedSharingTargetNames'

ntiid_fields = (NTIID, ntiid_)
creator_fields = (CREATOR, creator_)
oid_fields = (OID, p_oid_, oid_, id_)
keyword_fields = (keywords_, tags_, AUTO_TAGS)
container_id_fields = (CONTAINER_ID, 'ContainerID', containerId_, 'container')
last_modified_fields =  (ext_interfaces.StandardInternalFields.LAST_MODIFIED,
						 ext_interfaces.StandardInternalFields.LAST_MODIFIEDU,
						 LAST_MODIFIED,
						 last_modified_)

nti_mimetype_prefix = MIME_BASE + '.'

note_ = u'note'
canvas_ = u'canvas'
highlight_ = u'highlight'
redaction_ = u'redaction'
messageinfo = u'messageinfo'
messageinfo_ = u'messageinfo'
canvastextshape_ = 'canvastextshape'

indexable_type_names = (note_, highlight_, redaction_, messageinfo_)
indexable_types_order = { x:p for p,x in enumerate(indexable_type_names) }

def epoch_time(dt):
	if dt:
		seconds = mktime(dt.timetuple())
		seconds += (dt.microsecond / 1000000.0)
		return seconds
	else:
		return 0

def get_datetime(x=None):
	f = time.time()
	if x:
		f = float(x) if isinstance(x, six.string_types) else x
	return datetime.fromtimestamp(f)

def normalize_type_name(x, encode=True):
	result = ''
	if x:
		result =x[0:-1].lower() if x.endswith('s') else x.lower()
	return unicode(result) if encode else result

def get_type_name(obj):
	if not isinstance(obj, dict):
		result = obj.__class__.__name__
	elif CLASS in obj:
		result = obj[CLASS]
	elif MIME_TYPE in obj:
		result = obj[MIME_TYPE]
		if result and result.startswith(nti_mimetype_prefix):
			result = result[len(nti_mimetype_prefix):]
	else:
		result = None
	return normalize_type_name(result) if result else u''

class QueryExpr(object):
	def __init__(self, expr):
		assert expr is not None, 'must specify a query expression'
		self.expr = unicode(expr)

	def __str__( self ):
		return self.expr

	def __repr__( self ):
		return 'QueryExpr(%s)' % self.expr

_all_re = re.compile('([\?\*])')
def is_all_query(query):
	mo = _all_re.search(query)
	return mo and mo.start(1) == 0

def to_list(data):
	if isinstance(data, six.string_types):
		data = [data]
	elif isinstance(data, list):
		pass
	elif isinstance(data, collections.Iterable):
		data = list(data)
	elif data is not None:
		data = [data]
	return data

def sort_search_types(type_names=indexable_type_names):
	type_names = to_list(type_names)
	result = sorted(type_names, key=lambda x: indexable_types_order.get(x,0))
	return result
