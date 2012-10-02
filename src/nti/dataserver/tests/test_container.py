#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""

from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, greater_than
from hamcrest import has_property
from hamcrest import has_length
from hamcrest import same_instance
from hamcrest import none

from nose.tools import assert_raises

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

def test_case_insensitive_container_invalid_keys():

	c = container.CaseInsensitiveLastModifiedBTreeContainer()

	with assert_raises(TypeError):
		c.get( {} )

	with assert_raises(TypeError):
		c.get( 1 )


from zope.component.eventtesting import getEvents, clearEvents
def test_eventless_container():

	# The container doesn't proxy, fire events, or examine __parent__ or __name__
	c = container.EventlessLastModifiedBTreeContainer()

	clearEvents()

	value = object()
	value2 = object()
	c['key'] = value
	assert_that( c['key'], is_( same_instance( value ) ) )
	assert_that( getEvents(), has_length( 0 ) )
	assert_that( c, has_length( 1 ) )

	# We cannot add duplicates
	with assert_raises( KeyError ):
		c['key'] = value2

	# We cannot add None values or non-unicode keys
	with assert_raises( TypeError ):
		c['key2'] = None

	with assert_raises( TypeError ):
		c[None] = value

	with assert_raises( TypeError ):
		c[b'\xf0\x00\x00\x00'] = value

	# After all that, nothing has changed
	assert_that( c['key'], is_( same_instance( value ) ) )
	assert_that( getEvents(), has_length( 0 ) )
	assert_that( c, has_length( 1 ) )

	del c['key']
	assert_that( c.get('key'), is_( none() ) )
	assert_that( getEvents(), has_length( 0 ) )
	assert_that( c, has_length( 0 ) )
