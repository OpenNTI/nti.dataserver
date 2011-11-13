
from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, has_length, none)
import unittest
import datetime

import nti.dataserver.ntiids as ntiids


class TestNTIIDS(unittest.TestCase):

	def test_make_ntiid( self ):
		self.assertRaises( ValueError, ntiids.make_ntiid )
		self.assertRaises( ValueError, ntiids.make_ntiid, provider='foo', specific='baz' )

		assert_that( ntiids.make_ntiid( date=None, nttype='Test' ),
					 is_( 'tag:nextthought.com,%s:Test' % datetime.date.today().isoformat() ) )
		assert_that( ntiids.make_ntiid( date=None, nttype='Test', provider='TestP' ),
					 is_( 'tag:nextthought.com,%s:TestP-Test' % datetime.date.today().isoformat() ) )
		assert_that( ntiids.make_ntiid( date=None, nttype='Test', provider='TestP', specific='Bar' ),
					 is_( 'tag:nextthought.com,%s:TestP-Test-Bar' % datetime.date.today().isoformat() ) )

