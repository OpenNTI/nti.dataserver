#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals



from hamcrest import assert_that
from hamcrest import instance_of
from hamcrest import has_property
from hamcrest import contains
from hamcrest import starts_with


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve25 import evolve


from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas, CanvasUrlShape, NonpersistentCanvasUrlShape

import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings



class TestEvolve25(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve25(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			# Give me some data to migrate over
			note = Note()
			canvas = Canvas()
			shape = CanvasUrlShape() # A persistent object
			canvas.append( shape )
			shape.__parent__ = None
			shape._head = 'data:image/gif;base64'
			shape._raw_tail = 'these bytes do not make sense'
			note.body = [canvas]
			note.containerId = "foo:bar"
			jason.addContainedObject( note )
			note_id = note.id



		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			note = jason.getContainedObject( "foo:bar", note_id )

			assert_that( note, has_property( 'body', contains( has_property( 'shapeList', contains( instance_of( NonpersistentCanvasUrlShape ) ) ) ) ) )
			canvas = note.body[0]
			assert_that( canvas, has_property( '__parent__', note ) )

			shape = canvas.shapeList[0]
			assert_that( shape, has_property( '__parent__', canvas ) )
			assert_that( shape, has_property( '__name__', "0" ) )

			assert_that( shape, has_property( '_file' ) )
			assert_that( shape, has_property( 'url', starts_with( 'data:' ) ) )
