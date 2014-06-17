#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search query implementation.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
import hashlib

from zope import component
from zope import interface

from nti.externalization.externalization import make_repr

from nti.utils.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import constants
from . import interfaces as search_interfaces

phrase_search = re.compile(r'"(?P<text>.*?)"')
prefix_search = re.compile(r'(?P<text>[^ \t\r\n*]+)[*](?= |$|\\)')

def is_phrase_search(term):
	return phrase_search.match(term) is not None if term else False

def is_prefix_search(term):
	return prefix_search.match(term) is not None if term else False

@interface.implementer(search_interfaces.ISearchQuery)
@component.adapter(basestring)
def _default_query_adapter(query, *args, **kwargs):
	if query is not None:
		query = QueryObject.create(query, *args, **kwargs)
	return query

@interface.implementer(search_interfaces.IDateTimeRange)
class DateTimeRange(SchemaConfigured):
	
	__external_can_create__ = True
	mime_type = mimeType = 'application/vnd.nextthought.search.datetimerange'

	createDirectFieldProperties(search_interfaces.IDateTimeRange)

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or (self.startTime == other.startTime and
									 self.endTime == other.endTime)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.endTime)
		xhash ^= hash(self.startTime)
		return xhash

	def digest(self):
		md5 = hashlib.md5()
		md5.update(str(self.endTime))
		md5.update(str(self.startTime))
		result = md5.hexdigest()
		return result

@interface.implementer(search_interfaces.ISearchQuery)
class QueryObject(SchemaConfigured):

	__external_can_create__ = True
	__external_class_name__ = 'SearchQuery'

	mime_type = mimeType = 'application/vnd.nextthought.search.query'

	createDirectFieldProperties(search_interfaces.ISearchQuery)

	def __str__(self):
		return self.term

	__repr__ = make_repr()

	def __getitem__(self, key):
		return getattr(self, key)

	def __setitem__(self, key, val):
		setattr(self, key, val)

	@property
	def query(self):
		return self.term

	@property
	def content_id(self):
		return self.indexid

	@property
	def IsEmpty(self):
		return not self.term
	is_empty = IsEmpty

	@property
	def IsPhraseSearch(self):
		return is_phrase_search(self.term)
	is_phrase_search = IsPhraseSearch

	@property
	def IsPrefixSearch(self):
		return is_prefix_search(self.term)
	is_prefix_search = IsPrefixSearch
	
	@property
	def IsDescendingSortOrder(self):
		return self.sortOrder == constants.descending_
	is_descending_sort_order = IsDescendingSortOrder

	@property
	def IsBatching(self):
		return True if self.batchStart is not None and self.batchSize else False
	is_batching = IsBatching
	
	def __eq__(self, other):
		try:
			return self is other or (self.term.lower() == other.term.lower())
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.term.lower())
		return xhash
	
	def digest(self):
		names = ('term', 'limit', 'indexid', 'prefix',
				 'threshold', 'maxdist', 'creator')
		md5 = hashlib.md5()
		for name in names:
			value = getattr(self, name, None)
			if value is not None:
				md5.update(str(value).lower())

		if self.applyHighlights:
			md5.update(str(self.maxchars).lower())
			md5.update(str(self.surround).lower())

		searchOn = sorted(self.searchOn or ())
		searchOn = ','.join(searchOn)
		md5.update(searchOn.lower())

		for name in ('creationTime', 'modificationTime'):
			value = getattr(self, name, None)
			if value is not None:
				md5.update(value.digest())

		result = md5.hexdigest()
		return result

	# ---------------

	@classmethod
	def create(cls, query, **kwargs):
		if isinstance(query, six.string_types):
			queryobject = QueryObject(term=query)
		else:
			if isinstance(query, QueryObject):
				if kwargs:
					queryobject = QueryObject()
					queryobject.__dict__.update(query.__dict__)
				else:
					queryobject = query

		for k, v in kwargs.items():
			if k and v is not None:
				queryobject[k] = v

		return queryobject
