#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import time
import unittest

from nti.contentsearch._redis_lock import Lock
from nti.contentsearch._redis_lock import LockTimeout

from nti.dataserver.tests import mock_redis

from nose.tools import assert_raises

class TestRedisLock(unittest.TestCase):

	def setUp(self):
		super(TestRedisLock, self).setUp()
		self.redis = mock_redis.InMemoryMockRedis()
		
	def test_simple_lock(self):
		with Lock(self.redis):
			pass
	
	def test_lock_timeout(self):
		l1 = Lock(self.redis)
		l2 = Lock(self.redis)
		with l1:
			with assert_raises(LockTimeout):
				l2.acquire()
		
	def test_crashed_client(self):
		l1 = Lock(self.redis, expires=0.5)
		l1.acquire()
		time.sleep(1.5)
		with Lock(self.redis):
			pass
