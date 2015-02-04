#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search common functions.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
import math
import time
from time import mktime
from datetime import datetime
from collections import Iterable

from zope import component

from .interfaces import ISearchTypeMetaData

from .constants import CLASS, MIME_TYPE
from .constants import transcript_, messageinfo_, nti_mimetype_prefix

_mappers = None
def get_type_mappers():
	global _mappers
	if not _mappers:
		result = []
		for _, m in component.getUtilitiesFor(ISearchTypeMetaData):
			result.append(m)
		_mappers = sorted(result, key=lambda m: m.Order)
	return _mappers

_indexable_types_names = None
def get_indexable_types():
	global _indexable_types_names
	if not _indexable_types_names:
		result = {m.Name for m in get_type_mappers()}
		_indexable_types_names = frozenset(result)
	return _indexable_types_names

_ugd_indexable_types = None
def get_ugd_indexable_types():
	global _ugd_indexable_types
	if not _ugd_indexable_types:
		result = {m.Name for m in get_type_mappers() if m.IsUGD}
		_ugd_indexable_types = frozenset(result)
	return _ugd_indexable_types

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
media_date_to_millis = video_date_to_millis

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
mediatimestamp_to_datetime = videotimestamp_to_datetime

def normalize_type_name(x):
	x = x.lower() if x else u''
	result = x[0:-1] if x.endswith('s') else x
	return unicode(result)

def get_type_name(obj):

	for m in get_type_mappers():
		if m.Interface.providedBy(obj):
			return m.Name

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
	for m in get_type_mappers():
		if m.Name == name:
			return m.MimeType
	return None

def get_type_from_mimetype(mt):
	mt = mt.lower() if mt else u''
	for m in get_type_mappers():
		if m.MimeType == mt:
			if m.Name == transcript_:  # transcript and messageinfo are the same
				return messageinfo_
			return m.Name
	return None

def get_mime_type_map():
	result = {}
	for m in get_type_mappers():
		result[m.MimeType] = m.Name
	return result

def is_all_query(query):
	mo = re.search('([\?\*])', query)
	return mo is not None and mo.start(1) == 0

def to_list(data):
	if isinstance(data, six.string_types):
		data = [data]
	elif isinstance(data, list):
		pass
	elif isinstance(data, Iterable):
		data = list(data)
	elif data is not None:
		data = [data]
	return data

def get_sort_order(type_name):
	m = component.queryUtility(ISearchTypeMetaData, name=type_name)
	return m.Order if m is not None else 0

def sort_search_types(type_names=()):
	type_names = to_list(type_names)
	result = sorted(type_names, key=lambda x: get_sort_order(x))
	return result
