#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

import fudge

import nti.tests
from nti.tests import verifiably_provides, validly_provides
from nti.tests import is_true, is_false

from nti.zodb import interfaces
from nti.zodb.tokenbucket import PersistentTokenBucket

def test_provides():
	bucket = PersistentTokenBucket(80, 1)
	assert_that( bucket, validly_provides( interfaces.ITokenBucket ) )

@fudge.patch('nti.zodb.tokenbucket.time')
def test_consume(fudge_time):

	fudge_time.is_callable()
	fudge_time.returns( 0 )
	bucket = PersistentTokenBucket( 2 )

	assert_that( bucket, validly_provides( interfaces.ITokenBucket ) )

	# at time 0, the bucket has two tokens in it
	assert_that( bucket.consume( ), is_true() )
	assert_that( bucket.consume( ), is_true() )

	# Which are now gone
	assert_that( bucket.consume( ), is_false() )

	# If we strobe the clock forward, we can get another token, since
	# we are refilling at one per second
	fudge_time.returns( 1 )

	assert_that( bucket.consume( ), is_true() )
	assert_that( bucket.consume( ), is_false() )

	# skip forward two seconds, and we can consume both tokens again
	fudge_time.returns( 3 )
	assert_that( bucket.consume( 2 ), is_true() )
	assert_that( bucket.consume( ), is_false() )

	# cover
	assert_that( repr(bucket), is_( 'PersistentTokenBucket(2.0,1.0)' ) )

@fudge.patch('nti.zodb.tokenbucket.time', 'nti.zodb.tokenbucket.sleep')
def test_wait(fudge_time, fudge_sleep):

	fudge_time.is_callable()
	fudge_time.returns( 0 )
	bucket = PersistentTokenBucket( 2 )

	# at time 0, the bucket has two tokens in it
	assert_that( bucket.wait_for_token( ), is_true() )
	assert_that( bucket.wait_for_token( ), is_true() )

	# Which are now gone
	assert_that( bucket.consume( ), is_false() )

	fudge_sleep.is_callable()
	def _sleep(how_long):
		# If we strobe the clock forward, we can get another token, since
		# we are refilling at one per second
		assert_that( how_long, is_( 1.0 ) )
		fudge_time.returns( 1 )

	fudge_sleep._callable.call_replacement = _sleep
	# Sleep gets called, strobes the clock, and we move forward
	assert_that( bucket.wait_for_token( ), is_true() )
