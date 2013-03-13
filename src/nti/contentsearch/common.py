# -*- coding: utf-8 -*-
"""
Search common functions.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six
import time
import collections
from time import mktime
from datetime import datetime

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from . import interfaces as search_interfaces

from .constants import (CLASS, MIME_TYPE)
from .constants import (content_, post_, indexable_types_order, indexable_type_names,
						transcript_, messageinfo_, nti_mimetype_prefix)

def epoch_time(dt):
	if dt:
		seconds = mktime(dt.timetuple())
		seconds += (dt.microsecond / 1000000.0)
		return seconds
	else:
		return 0

def get_datetime(x=None):
	f = time.time()
	if x: f = float(x) if isinstance(x, six.string_types) else x
	return datetime.fromtimestamp(f)

def normalize_type_name(x, encode=True):
	result = ''
	if x: result = x[0:-1].lower() if x.endswith('s') else x.lower()
	return unicode(result) if encode else result

def get_type_name(obj):
	if search_interfaces.IBookContent.providedBy(obj):
		result = content_
	elif not isinstance(obj, dict):
		result = post_ if frm_interfaces.IPost.providedBy(obj) else obj.__class__.__name__
	elif CLASS in obj:
		result = obj[CLASS]
	elif MIME_TYPE in obj:
		result = obj[MIME_TYPE]
		if result and result.startswith(nti_mimetype_prefix):
			result = result[len(nti_mimetype_prefix):]
	else:
		result = None
	return normalize_type_name(result) if result else u''

def get_type_from_mimetype(mt):
	mt = mt.lower() if mt else u''
	if mt.startswith(nti_mimetype_prefix):
		result = mt[len(nti_mimetype_prefix):]
		result = messageinfo_ if result == transcript_ else result
		result = post_ if result.startswith('personalblog') else result
		result = result if result in indexable_type_names else None
	else:
		result = None
	return normalize_type_name(result) if result else None

class QueryExpr(object):
	def __init__(self, expr):
		assert expr is not None, 'must specify a query expression'
		self.expr = unicode(expr)

	def __str__(self):
		return self.expr

	def __repr__(self):
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

def get_sort_order(type_name):
	return indexable_types_order.get(type_name, 0)

def sort_search_types(type_names=indexable_type_names):
	type_names = to_list(type_names)
	result = sorted(type_names, key=lambda x: indexable_types_order.get(x, 0))
	return result
