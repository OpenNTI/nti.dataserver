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

from .pyramid import raise_field_error

# item/array functions

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

def is_valid_timestamp(ts):
	try:
		ts = float(ts)
		return ts >= 0
	except:
		return False

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

# meta classes

class MetaStoreObject(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		clazzname = getattr(cls, '__external_class_name__', name)
		t.mimeType = nti_mimetype_with_class(clazzname)
		# legacy, deprecated
		t.mime_type = t.mimeType
		# IContentTypeAware
		t.parameters = dict()
		return t

# data structures

class CaseInsensitiveDict(dict):

	def __init__(self, **kwargs):
		super(CaseInsensitiveDict, self).__init__()
		for key, value in kwargs.items():
			self.__setitem__(key, value)

	def has_key(self, key):
		return key.lower() in self.data

	def __setitem__(self, key, value):
		super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

	def get(self, key, default=None):
		return super(CaseInsensitiveDict, self).get(key.lower(), default)

	def __getitem__(self, key):
		return super(CaseInsensitiveDict, self).__getitem__(key.lower())

	def __delitem__(self, key):
		return super(CaseInsensitiveDict, self).__delitem__(key.lower())

