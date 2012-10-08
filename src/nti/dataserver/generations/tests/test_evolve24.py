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



from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve24 import evolve

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas, CanvasCircleShape, NonpersistentCanvasCircleShape

import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS
from nti.dataserver.tests import mock_dataserver
import fudge

from nti.deprecated import hides_warnings



class TestEvolve24(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve24(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			#install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )

			# Give me some data to migrate over
			note = Note()
			canvas = Canvas()
			canvas.append( CanvasCircleShape() )
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

			assert_that( note, has_property( 'body', contains( has_property( 'shapeList', contains( instance_of( NonpersistentCanvasCircleShape ) ) ) ) ) )
