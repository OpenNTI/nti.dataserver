#!/usr/bin/env python
from __future__ import unicode_literals, print_function

from hamcrest import assert_that, is_, less_than, greater_than, less_than_or_equal_to
from hamcrest import same_instance
from hamcrest import has_property

from nti.zodb.minmax import MergingCounter, NumericMinimum, NumericMaximum, ConstantZeroValue

from nose.tools import assert_raises
import cPickle as pickle

def test_comparisons():
	mc1 = MergingCounter()
	mc2 = MergingCounter()

	assert_that( mc1, is_( mc2 ) )
	mc2.increment()

	assert_that( mc1, is_( less_than( mc2 ) ) )
	assert_that( mc2, is_( greater_than( mc1 ) ) )

	mc1.increment()
	assert_that( mc1, is_( less_than_or_equal_to( mc2 ) ) )

	assert_that( hash(mc1), is_( mc1.value ) )

def test_merge_resolve():

	assert_that( MergingCounter()._p_resolveConflict( 0, 0, 1 ), is_( 1 ) )
	# simultaneous increment adds
	assert_that( MergingCounter()._p_resolveConflict( 0, 1, 1 ), is_( 2 ) )

def test_min_resolve():

	assert_that( NumericMinimum()._p_resolveConflict( 0, 0, 1 ), is_( 0 ) )
	# simultaneous increment adds
	assert_that( NumericMinimum()._p_resolveConflict( 3, 4, 2 ), is_( 2 ) )


def test_str():

	mc = MergingCounter()
	assert_that( str(mc), is_( "0" ) )
	assert_that( repr(mc), is_( "MergingCounter(0)" ) )

	mc.set( 1 )
	assert_that( str(mc), is_( "1" ) )
	assert_that( repr(mc), is_( "MergingCounter(1)" ) )

def test_zero():
	czv = ConstantZeroValue()
	assert_that( czv, is_( same_instance( ConstantZeroValue() ) ) )
	assert_that( czv, has_property( 'value', 0 ) )

	# equality
	assert_that( czv, is_( czv ) )
	v = NumericMaximum()
	assert_that( czv, is_( v ) )
	assert_that( v, is_( czv ) )

	v.value = -1
	assert_that( v, is_( less_than( czv ) ) )

	v.value = 1
	assert_that( v, is_( greater_than( czv ) ) )

	czv.value = 1
	assert_that( czv, has_property( 'value', 0 ) )

	czv.set( 2 )
	assert_that( czv, has_property( 'value', 0 ) )

	with assert_raises( TypeError ):
		pickle.dumps( czv )

	with assert_raises( NotImplementedError ):
		czv._p_resolveConflict( None, None, None )
