from __future__ import print_function, unicode_literals

import six
import UserDict

from zope import interface

from nti.contentsearch.common import to_list
from nti.contentsearch import interfaces as search_interfaces

@interface.implementer(search_interfaces.ISearchQuery)
class QueryObject(object, UserDict.DictMixin):
	
	__float_properties__ = ('threshold',)
	__int_properties__ 	 = ('limit', 'maxdist', 'prefix', 'surround', 'maxchars', 'pagenum', 'pagelen')
	__properties__ 		 = ('term', 'books', 'indexid', 'searchon', 'username') + __int_properties__ + __float_properties__

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
		return 'QueryObject(%s)' % self._data

	def __getitem__(self, key):
		if key.lower() in self.__properties__:
			key = key.lower()
		return self._data[key]

	def __setitem__(self, key, val):
		key = key.lower()
		
		# check for alias
		key = 'term' if key == 'query' else key
		key = 'indexid' if key == 'indexname' else key
		key = 'searchon' if key == 'search_on' else key
		key = 'pagelen' if key == 'batchsize' else key
		key = 'pagenum' if key == 'batchstart' else key
				
		if key in self.__properties__:
			if key == 'term':
				self.set_term(val)
			elif key == 'pagelen':
				self.set_pagelen(val)
			elif key == 'pagenum':
				self.set_pagenum(val)
			elif key == 'searchon':
				self.set_searchon(val)
			elif key in self.__int_properties__:
				self._data[key] = int(val) if val is not None else val
			elif key in self.__float_properties__:
				self._data[key] = float(val) if val is not None else val
			else:
				self._data[key] = unicode(val) if isinstance(val, six.string_types) else val

	# -- search --

	@property
	def indexid(self):
		return self._data.get('indexid', None)

	@property
	def books(self):
		books = self._data.get('books', ())
		if not books:
			indexid = self._data.get('indexid', None)
			if indexid is not None:
				books = (indexid,)
		return books

	def get_searchon(self):
		result = self._data.get('searchon', None)
		return result

	def set_searchon(self, val):
		if isinstance(val, six.string_types):
			val = val.split(',')
		self._data['searchon'] = to_list(val) if val is not None else None
	
	searchon = property(get_searchon, set_searchon)
	search_on = searchon
	
	@property
	def username(self):
		return self._data.get('username', None)

	def get_term(self):
		return self._data['term']

	def set_term(self, term):
		self._data['term'] = unicode(term) if term is not None else term

	term = property(get_term, set_term)
	query = term
	word = query

	def get_pagelen(self):
		return self._data.get('pagelen', None)

	def set_pagelen(self, pagelen=None):
		pagelen = abs(int(pagelen)) if pagelen is not None else pagelen
		self._data['pagelen'] = pagelen

	pagelen = property(get_pagelen, set_pagelen)

	def get_pagenum(self):
		return self._data.get('pagenum', None)

	def set_pagenum(self, pagenum=None):
		pagenum = abs(int(pagenum)) if pagenum is not None else pagenum
		self._data['pagenum'] = pagenum

	pagenum = property(get_pagenum, set_pagenum)
	
	def get_limit(self):
		return self._data.get('limit', None)

	def set_limit(self, limit=None):
		limit = abs(int(limit)) if limit is not None else limit
		self._data['limit'] = limit

	limit = property(get_limit, set_limit)
	
	def get_subqueries(self):
		result = []
		for k in self.keys():
			if k not in self.__properties__:
				result.append( (k, self._data.get(k)) )
		return result

	@property
	def num_subqueries(self):
		result = 0
		for k in self.keys():
			if k not in self.__properties__:
				result = result + 1
		return result

	@property
	def is_empty(self):
		return not self.term

	# -- suggest --

	def get_maxdist(self):
		return self._data.get('maxdist', None)

	def set_maxdist(self, maxdist):
		self.__setitem__('maxdist', maxdist)

	maxdist = property(get_maxdist, set_maxdist)

	def get_prefix(self):
		return self._data.get('prefix', None)

	def set_prefix(self, prefix):
		self.__setitem__('prefix', prefix)

	prefix = property(get_prefix, set_prefix)

	def get_threshold(self):
		return self._data.get('threshold', 0.4999)

	def set_threshold(self, threshold):
		self.__setitem__('threshold', threshold)

	threshold = property(get_threshold, set_threshold)

	# -- highlight --

	def get_surround(self):
		return self._data.get('surround', 20)

	def set_surround(self, surround=20):
		self.__setitem__('surround', surround)

	surround = property(get_surround, set_surround)

	def get_maxchars(self):
		return self._data.get('maxchars', 300)

	def set_maxchars(self, maxchars=300):
		self.__setitem__('maxchars', maxchars)

	maxchars = property(get_maxchars, set_maxchars)

	# ---------------

	@classmethod
	def parse_query_properties(cls, **kwargs):
		result = {}
		for k, v in kwargs.items():
			if k.lower() in cls.__properties__:
				result[k] = v
		return result

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
