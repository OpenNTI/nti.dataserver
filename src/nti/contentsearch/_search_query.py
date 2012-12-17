from __future__ import print_function, unicode_literals

import re
import six
import sys
import UserDict
import collections

from zope import component
from zope import interface

from nti.contentsearch.common import descending_
from nti.contentsearch import interfaces as search_interfaces

phrase_search = re.compile(r'"(?P<text>.*?)"')
prefix_search = re.compile(r'(?P<text>[^ \t\r\n*]+)[*](?= |$|\\)')

@interface.implementer(search_interfaces.ISearchQuery)
@component.adapter(basestring)
def _default_query_adapter(query, *args, **kwargs):
	if query is not None:
		query = QueryObject.create(query, *args, **kwargs)
	return query
	
def _getter(name, default=None):
	def function(self):
		return self._data.get(name, default)
	return function

def _setter_str(name, default=None):
	def function(self, val):
		val = val or default
		val = unicode(val) if isinstance(val, six.string_types) else repr(val)
		self._data[name] = val
	return function

def _setter_int(name, _abs=True):
	def function(self, val):
		if val is not None:
			val = abs(int(val)) if _abs else int(val)
		self._data[name] = val
	return function

def _setter_float(name, _abs=True):
	def function(self, val):
		if val is not None:
			val = abs(float(val)) if _abs else float(val)
		self._data[name] = val
	return function

def _setter_tuple(name, unique=True):
	def function(self, val):
		if val is not None:
			if isinstance(val, (list, tuple)) and len(val) == 1:
				val = val[0]
			if isinstance(val, six.string_types):
				val = val.split(',')
			if not isinstance(val, collections.Iterable):
				val = list(val)
			val = tuple(set(val)) if unique else tuple(val)
		self._data[name] = val
	return function

class _MetaQueryObject(type):
	
	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		
		# string properties
		for name in t.__str_properties__:
			df = t.__defaults__.get(name, None)
			setattr(t, name, property(_getter(name, df), _setter_str(name)))
		setattr(t, 'query', property(_getter('term'), _setter_str('term')))
		
		# int properties
		for name in t.__int_properties__:
			df = t.__defaults__.get(name, None)
			setattr(t, name, property(_getter(name, df), _setter_int(name)))
		
		# float properties
		for name in t.__float_properties__:
			df = t.__defaults__.get(name, None)
			setattr(t, name, property(_getter(name, df), _setter_float(name)))
			
		# set properties
		for name in t.__set_properties__:
			df = t.__defaults__.get(name, None)
			setattr(t, name, property(_getter(name, df), _setter_tuple(name)))
			
		return t
	
_empty_subqueries = {}

@interface.implementer(search_interfaces.ISearchQuery)
class QueryObject(object, UserDict.DictMixin):
	
	__metaclass__ = _MetaQueryObject
	
	__float_properties__ = ('threshold',)
	__int_properties__ 	 = ('limit', 'maxdist', 'prefix', 'surround', 'maxchars', 'batchSize', 'batchStart')
	__str_properties__ 	 = ('term', 'indexid', 'username', 'location', 'sortOn', 'sortOrder')
	__set_properties__	 = ('searchOn',)
	__properties__ 		 = __set_properties__ + __str_properties__ + __int_properties__ + __float_properties__

	__defaults__ 		 = {'surround': 20, 'maxchars' : 300, 'threshold' : 0.4999, 'sortOrder':descending_ ,
							'limit': sys.maxint}
	
	def __init__(self, *args, **kwargs):
		self._data = {}
		for k, v in kwargs.items():
			if k and v is not None:
				self.__setitem__(k, v)

	def keys(self):
		return self._data.keys()

	def __str__( self ):
		return self.term

	def __repr__( self ):
		return 'QueryObject(%r)' % self._data

	def __getitem__(self, key):
		return self._data[key]

	def __setitem__(self, key, val):
		if hasattr(self, key):
			setattr(self, key, val)
		else:
			self._data[key] = unicode(val) if isinstance(val, six.string_types) else val

	# -- search --
	
	@property
	def is_empty(self):
		return not self.term
	
	@property
	def is_phrase_search(self):
		return phrase_search.match(self.term) is not None if self.term else False
	
	@property
	def is_prefix_search(self):
		return prefix_search.match(self.term) is not None if self.term else False

	@property
	def is_descending_sort_order(self):
		return self.sortOrder == descending_
	
	# ---------------

	@classmethod
	def create(cls, query, **kwargs):
		if isinstance(query, six.string_types):
			queryobject = QueryObject(term=query)
		else:
			if isinstance(query, QueryObject):
				if kwargs:
					queryobject = QueryObject()
					queryobject._data.update(query._data)
				else:
					queryobject = query

		for k, v in kwargs.items():
			if k and v is not None:
				queryobject[k] = v

		return queryobject
