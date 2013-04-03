# -*- coding: utf-8 -*-
"""
Store utils module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six

def from_delimited(value, delim=','):
	result = value.split(delim)
	result = re.findall("[^\s]+", value) if len(result) <= 1 else result
	return result

def to_collection(items=None, factory=list):
	result = None
	if not items:
		result = factory()
	elif isinstance(items, factory):
		result = items
	elif isinstance(items, six.string_types):
		result = factory(from_delimited(unicode(items)))
	else:
		result = factory(items)
	return result

def to_list(items=None):
	return to_collection(items, list)

def to_frozenset(items=None):
	return to_collection(items, frozenset)
