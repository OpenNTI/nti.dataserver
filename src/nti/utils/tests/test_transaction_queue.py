#!/usr/bin/env python

from __future__ import print_function, unicode_literals

from nti.tests import AbstractTestBase
from hamcrest import assert_that, is_

import transaction

import gevent.queue
from gevent.queue import Queue

from nti.utils.transaction_queue import put_nowait

class PutQueueTest(AbstractTestBase):

	def test_put_succeeds(self):
		queue = Queue() # unbounded
		transaction.begin()

		put_nowait( queue, self )
		# still empty
		assert_that( queue.qsize(), is_( 0 ) )

		transaction.commit()

		assert_that( queue.get(block=False), is_( self ) )

	def test_put_failure( self ):
		queue = Queue(1) # unbounded
		queue.put( object() )
		assert_that( queue.qsize(), is_( 1 ) )

		transaction.begin()

		put_nowait( queue, self )
		# still size 1
		assert_that( queue.qsize(), is_( 1 ) )
		with self.assertRaises( gevent.queue.Full ) as cm:
			transaction.commit()


		assert_that( cm.exception, is_( gevent.queue.Full ) )
		assert_that( queue.get(block=False), is_( object ) )
