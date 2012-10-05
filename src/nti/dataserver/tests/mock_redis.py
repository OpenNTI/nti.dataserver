#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Trivial implementation of the basic parts of an in-memory redis-like implementation.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from hamcrest import assert_that
from hamcrest import is_

@interface.implementer(nti_interfaces.IRedisClient)
class InMemoryMockRedis(object):


	def __init__( self ):
		self.database = {}

	###
	# Basic
	###

	def set( self, key, value ):
		self.database[key] = value

	def get( self, key ):
		return self.database.get( key )

	def delete( self, key ):
		self.database.pop( key, None )

	def expire( self, key, ttl ):
		pass

	def rename(self, old_key, new_key):
		if new_key in self.database:
			raise ValueError("key '%s' already in database" % new_key)
		
		if old_key not in self.database:
			raise KeyError(old_key)
		
		value = self.database.pop( old_key )
		self.database[new_key] = value
	
	###
	# Pipeline
	###

	def pipeline(self):
		"""
		Our implementation of pipelining is trivial: we return
		an object that assumes that execute is going to be called immediately.
		"""
		return Pipeline(self)

	###
	# List operations
	###

	def lrange( self, key, start, end ):
		obj = self.get( key )
		if obj is None:
			return ()
		assert_that( obj, is_( list ) )
		if end == -1:
			return obj[start:]
		return obj[start:end]

	def rpush( self, key, value ):
		q = self.get( key )
		if q is None:
			q = self.database[key] = list()
		q.append( value )
		
	###
	# Set operations
	###

	def sadd(self, key, *args):
		s = self.database.get(key, None)
		if s is None:
			s = set()
			self.database[key] = s
		assert_that( s, is_( set ) )
		result = 0
		for a in args:
			if a not in s:
				s.add(a)
				result += 1
		return result
	
	def scard(self, key):
		s = self.database.get(key, None)
		result = 0
		if s is not None:
			assert_that( s, is_( set ) )
			result = len(s)
		return result
	
	def srem(self, key, *args):
		s = self.database.get(key, None)
		result = 0
		if s is not None:
			assert_that( s, is_( set ) )
			for a in args:
				if a in s:
					s.remove(a)
					result += 1
		return result
	
	def smembers(self, key):
		s = self.database.get(key, set())
		assert_that( s, is_( set ) )
		return s
	
	def sismember(self, key, val):
		s = self.database.get(key, None)
		result = 0
		if s is not None:
			assert_that( s, is_( set ) )
			result = 1 if val in s else 0
		return result
	
class Pipeline(object):

	def __init__( self, redis ):
		self._redis = redis
		self._results = []

	def __getattr__( self, key ):
		meth = getattr( self._redis, key )
		def call(*args):
			r = meth(*args)
			self._results.append( r )
			return self
		return call

	def execute( self ):
		return self._results
