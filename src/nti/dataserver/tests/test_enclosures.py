#!/usr/bin/env python2.7

from hamcrest import assert_that, is_not, is_in, is_, has_entry

from .. import enclosures
from .. import interfaces

from . import implements

from . import mock_dataserver

class TestSimpleEnclosureMixin(mock_dataserver.ConfiguringTestBase):
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

		sem.add_enclosure( content2 )
		assert_that( content.name, is_('Name') )
		assert_that( sem.enclosures, has_entry( 'Name', content ) )
		assert_that( content2.name, is_( 'Name-2' ) )
		assert_that( sem.enclosures, has_entry( 'Name-2', content2 ) )

		assert_that( list( sem.iterenclosures() ), is_( [content,content2] ) )
