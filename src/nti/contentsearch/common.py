# -*- coding: utf-8 -*-
"""
Search common functions.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
import math
import time
import collections
from time import mktime
from datetime import datetime

from zope import component

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from nti.externalization import interfaces as ext_intefaces

from . import interfaces as search_interfaces

from .constants import (CLASS, MIME_TYPE, BOOK_CONTENT_MIME_TYPE, POST_MIME_TYPE,
						VIDEO_TRANSCRIPT_MIME_TYPE, NTI_CARD_MIME_TYPE)

from .constants import (content_, post_, note_, highlight_, redaction_,
						indexable_types_order, indexable_type_names, transcript_,
						messageinfo_, nti_mimetype_prefix, videotranscript_, nticard_)

# Make sure we keep this order, especially since we need to test first for INote before IHighlight
interface_to_indexable_types = (
	(search_interfaces.IBookContent, content_),
	(search_interfaces.IVideoTranscriptContent, videotranscript_),
	(search_interfaces.INTICardContent, nticard_),
	(nti_interfaces.INote, note_),
	(nti_interfaces.IHighlight, highlight_),
	(nti_interfaces.IRedaction, redaction_),
	(chat_interfaces.IMessageInfo, messageinfo_),
	(forum_interfaces.IPost, post_))

mime_type_map = None

def epoch_time(dt):
	if dt:
		seconds = mktime(dt.timetuple())
		seconds += (dt.microsecond / 1000000.0)
		return seconds
	return 0

def get_datetime(x=None):
	x = x or time.time()
	return datetime.fromtimestamp(float(x))

def date_to_videotimestamp(dt):
	dt = float(dt) if isinstance(dt, six.string_types) else dt
	dt = get_datetime(dt) if isinstance(dt, (float, long)) else dt
	if isinstance(dt, datetime):
		milli = math.floor(dt.microsecond / 1000.0)
		result = u"%02d:%02d:%02d.%03d" % (dt.hour, dt.minute, dt.second, milli)
		return result
	return u''

def video_date_to_millis(dt):
	start = datetime(year=1, month=1, day=1)
	diff = dt - start
	return diff.total_seconds() * 1000.0

def videotimestamp_to_datetime(qstring):
	# this method parses a timestamp of the form hh:mm::ss.uuu
	qstring = qstring.replace(" ", "")
	year = month = day = 1
	hour = minute = second = microsecond = 0
	if len(qstring) >= 2:
		hour = int(qstring[0:2])
	if len(qstring) >= 5:
		minute = int(qstring[3:5])
	if len(qstring) >= 8:
		second = int(qstring[6:8])
	if len(qstring) == 12:
		microsecond = int(qstring[9:12]) * 1000
	if len(qstring) == 13:
		microsecond = int(qstring[9:13])

	result = datetime(year=year, month=month, day=day, hour=hour,
			 		  minute=minute, second=second, microsecond=microsecond)
	return result

def normalize_type_name(x):
	x = x.lower() if x else u''
	result = x[0:-1] if x.endswith('s') else x
	return unicode(result)

def get_type_name(obj):

	for iface, type_ in interface_to_indexable_types:
		if iface.providedBy(obj):
			return type_

	# legacy and test purpose
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

def get_mimetype_from_type(name):
	name = name.lower() if name else u''
	mmap = get_mime_type_map()
	for k, v in mmap.items():
		if v == name:
			return k
	return None

def get_type_from_mimetype(mt):
	mt = mt.lower() if mt else u''
	mmap = get_mime_type_map()
	result = mmap.get(mt, None)
	if result is None and mt.startswith(nti_mimetype_prefix):
		result = mt[len(nti_mimetype_prefix):]
		if result == transcript_:
			result = messageinfo_
	result = result if result in indexable_type_names else None
	return normalize_type_name(result) if result else None

def get_mime_type_map():
	global mime_type_map
	if not mime_type_map:
		mime_type_map = {}
		utils = component.getUtilitiesFor(ext_intefaces.IMimeObjectFactory)
		for mime_type, utility in utils:
			ifaces = utility.getInterfaces()
			for iface in ifaces:
				for indexable, type_name in interface_to_indexable_types:
					if iface.extends(indexable, strict=False):
						mime_type_map[mime_type] = type_name
						break
				if mime_type in mime_type_map:
					break
		if mime_type_map:
			mime_type_map[POST_MIME_TYPE] = post_
			mime_type_map[NTI_CARD_MIME_TYPE] = nticard_
			mime_type_map[BOOK_CONTENT_MIME_TYPE] = content_
			mime_type_map[VIDEO_TRANSCRIPT_MIME_TYPE] = videotranscript_

	return mime_type_map

def is_all_query(query):
	mo = re.search('([\?\*])', query)
	return mo is not None and mo.start(1) == 0

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

def get_sort_order(type_name):
	return indexable_types_order.get(type_name, 0)

def sort_search_types(type_names=indexable_type_names):
	type_names = to_list(type_names)
	result = sorted(type_names, key=lambda x: indexable_types_order.get(x, 0))
	return result
