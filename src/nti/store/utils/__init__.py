# -*- coding: utf-8 -*-
"""
Store utils module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six

from nti.mimetype.mimetype import nti_mimetype_with_class

def from_delimited(value, delim=' '):
	result = value.split(delim)
	result = re.findall("[^\s]+", value) if len(result) <= 1 else result
	return result

def to_collection(items=None, factory=list, delim=' '):
	result = None
	if not items:
		result = factory()
	elif isinstance(items, factory):
		result = items
	elif isinstance(items, six.string_types):
		result = factory(from_delimited(unicode(items), delim))
	else:
		result = factory(items)
	return result

def to_list(items=None, delim=' '):
	return to_collection(items, list)

def to_frozenset(items=None, delim=' '):
	return to_collection(items, frozenset, delim)

def is_valid_amount(amount):
	try:
		amount = float(amount)
		return amount > 0
	except:
		return False

def is_valid_pve_int(value):
	try:
		value = float(value)
		return value > 0
	except:
		return False

class MetaStoreObject(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.mimeType = nti_mimetype_with_class(name)
		# legacy, deprecated
		t.mime_type = t.mimeType
		# IContentTypeAware
		t.parameters = dict()
		return t
