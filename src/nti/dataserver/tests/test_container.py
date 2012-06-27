#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""

from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, greater_than
from hamcrest import has_property

import nti.tests
from nti.tests import verifiably_provides, is_true, is_false
import nti.dataserver

from nti.dataserver import containers as container, interfaces, datastructures

from zope import interface
from zope.container import contained

from zope import lifecycleevent

# Nose module-level setup and teardown
setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.dataserver,) )
tearDownModule = nti.tests.module_teardown

def test_lastModified_container_event():

	c = container.LastModifiedBTreeContainer()

	assert_that( c.lastModified, is_( 0 ) )

	c['k'] = contained.Contained()

	assert_that( c.lastModified, is_( greater_than( 0 ) ), "__setitem__ should change lastModified" )
	# reset
	c.lastModified = 0
	assert_that( c.lastModified, is_( 0 ) )

	del c['k']

	assert_that( c.lastModified, is_( greater_than( 0 ) ), "__delitem__ should change lastModified" )

	# coverage
	c.updateLastModIfGreater( c.lastModified + 100 )

def test_lastModified_in_parent_event():
	c = container.LastModifiedBTreeContainer()

	@interface.implementer(interfaces.ILastModified)
	class Contained(datastructures.CreatedModDateTrackingObject,contained.Contained):
		pass

	child = Contained()
	assert_that( child, verifiably_provides( interfaces.ILastModified ) )

	c['k'] = child
	# reset
	c.lastModified = 0
	assert_that( c.lastModified, is_( 0 ) )

	lifecycleevent.modified( child )

	assert_that( c.lastModified, is_( greater_than( 0 ) ), "changing a child should change lastModified" )

def test_case_insensitive_container():
	c = container.CaseInsensitiveLastModifiedBTreeContainer()

	child = contained.Contained()
	c['UPPER'] = child
	assert_that( child, has_property( '__name__', 'UPPER' ) )

	assert_that( c.__contains__( None ), is_false() )
	assert_that( c.__contains__( 'UPPER' ), is_true() )
	assert_that( c.__contains__( 'upper' ), is_true() )

	assert_that( c.__getitem__( 'UPPER' ), is_( child ) )
	assert_that( c.__getitem__( 'upper' ), is_( child ) )

	assert_that( list(iter(c)), is_( ['UPPER'] ) )
	assert_that( list(c.keys()), is_( ['UPPER'] ) )
	assert_that( list(c.keys('a')), is_( ['UPPER'] ) )
	assert_that( list(c.keys('A')), is_( ['UPPER'] ) )
	assert_that( list(c.iterkeys()), is_( ['UPPER'] ) )

	assert_that( list( c.items() ), is_( [('UPPER', child)] ) )
	assert_that( list( c.items('a') ), is_( [('UPPER', child)] ) )
	assert_that( list( c.items('A') ), is_( [('UPPER', child)] ) )
	assert_that( list( c.iteritems() ), is_( [('UPPER', child)] ) )

	assert_that( list( c.values() ), is_( [child] ) )
	assert_that( list( c.values('a') ), is_( [child] ) )
	assert_that( list( c.values('A') ), is_( [child] ) )
	assert_that( list( c.itervalues() ), is_( [child] ) )

	del c['upper']
