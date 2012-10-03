from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from hamcrest import (is_, assert_that)

@interface.implementer(nti_interfaces.IRedisClient)
class InMemoryMockRedis(object):

	def __init__( self ):
		self.database = {}

	def set( self, key, value ):
		self.database[key] = value

	def get( self, key ):
		return self.database.get( key )

	def delete( self, key ):
		self.database.pop( key, None )

	def expire( self, key, ttl ):
		pass

	def pipeline(self):
		return Pipeline(self)

	def lrange( self, key, start, end ):
		obj = self.get( key )
		if obj is None:
			return ()
		assert_that( obj, is_( list ) )
		if end == -1:
			return obj[start:]
		return obj[start:end]
	
	def ltrim( self, key, start, end ):
		obj = self.get( key )
		if obj is None:
			return ()
		assert_that( obj, is_( list ) )
		if end == -1:
			result = obj[start:]
		elif start <= end:
			result = obj[start:end]
		else:
			result = obj
			
		self.database[key] = result
		return result
	
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
