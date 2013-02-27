# -*- coding: utf-8 -*-
"""
A redis lock.

adpated from https://chris-lamb.co.uk/posts/distributing-locking-python-and-redis

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time

class LockTimeout(BaseException):
	pass

class Lock(object):
	def __init__(self, redis, key='mylock', expires=60, timeout=10):
		self.key = key
		self.redis = redis
		self.timeout = timeout
		self.expires = expires
	
	def acquire(self, blocking=False):
		timeout = self.timeout if blocking else 0
		while timeout >= 0:
			expires = time.time() + self.expires + 1

			if self.redis.setnx(self.key, expires):
				# We gained the lock; enter critical section
				return True

			current_value = self.redis.get(self.key)

			# We found an expired lock and nobody raced us to replacing it
			if 	current_value and float(current_value) < time.time() and \
				str(self.redis.getset(self.key, expires)) == str(current_value):
				return True

			timeout -= 1
			if timeout > 0:
				time.sleep(1)

		raise LockTimeout("Timeout while waiting for lock")
	
	def release(self):
		self.redis.delete(self.key)
		
	def __enter__(self):
		self.acquire(blocking=True)

	def __exit__(self, exc_type, exc_value, traceback):
		self.release()
