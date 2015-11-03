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
from time import mktime
from collections import Iterable

from zope import component

from nti.contentindexing.utils import get_datetime
from nti.contentindexing.utils import video_date_to_millis
from nti.contentindexing.utils import date_to_videotimestamp
from nti.contentindexing.utils import videotimestamp_to_datetime

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

# BWC
get_datetime = get_datetime
media_date_to_millis = video_date_to_millis
date_to_videotimestamp = date_to_videotimestamp
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
