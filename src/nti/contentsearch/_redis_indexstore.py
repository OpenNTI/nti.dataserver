from __future__ import print_function, unicode_literals

import zlib

import gevent

from zope import component
from ZODB import loglevels

from nti.dataserver import interfaces as nti_interfaces

SLEEP_WAIT_TIME = 10
EXPIRATION_TIME_IN_SECS = 60
DEFAULT_QUEUE_NAME = u'nti/cloudsearch'

import logging
logger = logging.getLogger( __name__ )

ADD_OPERATION = 'add'
UPDATE_OPERATION = 'update'
DELETE_OPERATION = 'delete'
		
_op_precedence = {ADD_OPERATION : 0, UPDATE_OPERATION: 1, DELETE_OPERATION: 2}

def sort_messages(msg_list):
	def m_cmp(a, b):
		r = cmp(a[2], b[2])
		if r == 0:
			r = cmp(a[1], b[1])
		if r == 0:
			o_a = _op_precedence.get(a[0], 0)
			o_b = _op_precedence.get(b[0], 0)
			r = cmp(o_a, o_b)
		return r
	return sorted(msg_list, cmp=m_cmp) 

class _RedisStorageService(object):
	
	_redis = None
	
	def __init__(self, 	queue_name=DEFAULT_QUEUE_NAME, 
						expiration_time=EXPIRATION_TIME_IN_SECS, 
						sleep_wait_time=SLEEP_WAIT_TIME):
		self._v_stop = False
		self._v_queue_name = queue_name
		self._v_sleep_wait_time = sleep_wait_time
		self._v_expiration_time = expiration_time
		self._v_index_listener = self._spawn_index_listener()

	def _get_redis( self ):
		if self._redis is None:
			self._redis = component.getUtility( nti_interfaces.IRedisClient )
		return self._redis
	
	@property
	def queue_name(self):
		return self._v_queue_name
	
	@property
	def expiration_time(self):
		return self._v_expiration_time
	
	@property
	def sleep_wait_time(self):
		return self._v_sleep_wait_time
	
	@property
	def batch_proc(self):
		return self._v_batch_proc
	
	@property
	def stop(self):
		return self._v_stop
	
	def halt(self):
		self._v_stop = True
		
	def encode_message(self, op, docid, username):
		msg = repr((op, docid, username))
		return msg
		
	def add(self, docid, username):
		msg = self.encode_message(ADD_OPERATION, docid, username)
		self._put_msg(msg)
	
	def update(self, docid, username):
		msg = self.encode_message(UPDATE_OPERATION, docid, username)
		self._put_msg(msg)
		
	def delete(self, docid, username):
		msg = self.encode_message(DELETE_OPERATION, docid, username)
		self._put_msg(msg)
	
	def _get_index_msgs(self):
		msgs, _ = self._get_redis().pipeline().lrange(self.queue_name, 0, -1).delete(self.queue_name).execute()
		return msgs
	
	def _put_msg(self, msg, queue_name=None):
		if msg is not None:
			msg = zlib.compress( msg )
			self._put_msg_to_redis(msg)
	
	def _put_msg_to_redis(self, msg):
		self._get_redis().pipeline().rpush(self.queue_name, msg).expire(self.queue_name, self.expiration_time).execute()
			
	def _spawn_index_listener(self):
		
		def read_index_msgs():
			while not self.stop:
				# wait for idx ops
				gevent.sleep(self.sleep_wait_time)
				if not self.stop:
					self.read_process_index_msgs()
				
		result = gevent.spawn( read_index_msgs )
		return result
	
	def _push_back_msgs(self, msgs, encode=True):
		if msgs:
			logger.info( "Pushing messages back onto %s on exception", self.queue_name )
			msgs.reverse()
			msgs = [zlib.compress(repr(m)) for m in msgs] if encode else msgs
			self._redis.lpush(self.queue_name, *msgs)
		
	def read_process_index_msgs(self):
		encoded_msgs = ()
		try:
			encoded_msgs = self._get_index_msgs()
			if encoded_msgs:
				msgs = [eval(zlib.decompress(m)) for m in encoded_msgs]
				logger.log(loglevels.TRACE, 'Processing %s index event(s) read from redis queue %r', len(encoded_msgs), self.queue_name)
				self.process_messages(msgs)			
		except Exception:
			self._push_back_msgs(encoded_msgs, encode=False)
			logger.exception( "Failed to read and process index messages" )
	
	def process_messages(self, msgs):
		pass
	
