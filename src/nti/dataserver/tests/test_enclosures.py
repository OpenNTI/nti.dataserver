#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that

import unittest

from .. import enclosures
from .. import interfaces

from . import implements

from . import mock_dataserver

class TestSimpleEnclosureMixin(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer
	def test_iface(self):
		assert_that( enclosures.SimplePersistentEnclosure, implements( interfaces.IEnclosedContent ))

	def test_add_enclosure(self):
		sem = enclosures.SimpleEnclosureMixin()

		# enclosures created on demand
		assert_that( '_enclosures', is_not( is_in( sem.__dict__ ) ) )
		assert_that( list(sem.iterenclosures()), is_( [] ) )

		# accepts None gracefully
		sem.add_enclosure( None )
		assert_that( '_enclosures', is_not( is_in( sem.__dict__ ) ) )

		with self.assertRaises(AttributeError):
			sem.add_enclosure( '' )

		class Content(object): pass
		content = Content()
		content.name = 'Name'

		sem.add_enclosure( content )
		# alias this object to ensure that it doesn't accidentally
		# get overwritten
		sem.enclosures = getattr( sem, '_enclosures' )
		assert_that( content.name, is_( 'Name' ) )
		assert_that( sem.enclosures, has_entry( 'Name', content ) )
		assert_that( list( sem.iterenclosures() ), is_( [content] ) )

		# Chooses names
		content2 = Content()
		content2.name = 'Name'

		sem._enclosures._v_nextid = 1 # deterministic ids
		sem.add_enclosure( content2 )
		assert_that( content.name, is_('Name') )
		assert_that( sem.enclosures, has_entry( 'Name', content ) )
		assert_that( content2.name, is_( 'Name.1' ) )
		assert_that( sem.enclosures, has_entry( 'Name.1', content2 ) )

		assert_that( list( sem.iterenclosures() ), is_( [content,content2] ) )
