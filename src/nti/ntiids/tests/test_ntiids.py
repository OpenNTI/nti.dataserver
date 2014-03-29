#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import time
import datetime
import unittest

import nti.ntiids.ntiids as ntiids

from nti.ntiids import interfaces

from nose.tools import assert_raises

from nti.testing.matchers import verifiably_provides

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

	def test_parse_ntiid( self ):
		ntiid = ntiids.get_parts( ntiids.ROOT )
		assert_that( ntiid, verifiably_provides( interfaces.INTIID ) )

	def test_utc_date( self ):
		"A timestamp should always be interpreted UTC."
		# This date is 2012-01-05 in UTC, but 2012-01-04 in CST
		assert_that( ntiids.make_ntiid( date=1325723859.140755, nttype='Test' ),
					 is_( 'tag:nextthought.com,2012-01-05:Test' ) )

	def test_make_safe( self ):
		assert_that( ntiids.make_specific_safe( 'Foo%Bar +baz.' ),
					 is_( 'Foo_Bar__baz_' ) )

		with assert_raises(ntiids.ImpossibleToMakeSpecificPartSafe):
			ntiids.make_specific_safe( '' ) # too short

		with assert_raises(ntiids.ImpossibleToMakeSpecificPartSafe):
			ntiids.make_specific_safe( '   ' ) # only invalid characters
