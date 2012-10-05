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
