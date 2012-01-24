
from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, has_length, none)
import unittest
import datetime
import time

import nti.dataserver.ntiids as ntiids


class TestNTIIDS(unittest.TestCase):

	def test_make_ntiid( self ):
		self.assertRaises( ValueError, ntiids.make_ntiid )
		self.assertRaises( ValueError, ntiids.make_ntiid, provider='foo', specific='baz' )
		iso_now = datetime.date( *time.gmtime()[:3] ).isoformat()
		assert_that( ntiids.make_ntiid( date=None, nttype='Test' ),
					 is_( 'tag:nextthought.com,%s:Test' % iso_now ) )
		assert_that( ntiids.make_ntiid( date=0, nttype='Test' ),
					 is_( 'tag:nextthought.com,%s:Test' % iso_now ) )

		assert_that( ntiids.make_ntiid( date=None, nttype='Test', provider='TestP' ),
					 is_( 'tag:nextthought.com,%s:TestP-Test' % iso_now ) )
		assert_that( ntiids.make_ntiid( date=None, nttype='Test', provider='TestP', specific='Bar' ),
					 is_( 'tag:nextthought.com,%s:TestP-Test-Bar' % iso_now ) )


	def test_utc_date( self ):
		"A timestamp should always be interpreted UTC."
		# This date is 2012-01-05 in UTC, but 2012-01-04 in CST
		assert_that( ntiids.make_ntiid( date=1325723859.140755, nttype='Test' ),
					 is_( 'tag:nextthought.com,2012-01-05:Test' ) )
