#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import fudge

import nti.dataserver
from nti.dataserver.generations.evolve34 import evolve
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas, CanvasPolygonShape, CanvasAffineTransform

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.deprecated import hides_warnings

from hamcrest import (assert_that, has_property, close_to)

class TestEvolve33(mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve32(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden' )

			note = Note()
			canvas = Canvas()
			square = CanvasPolygonShape(sides=4)
			tx = CanvasAffineTransform()
			tx.a = 0.0975
			tx.c = -0.005
			tx.b = 0.005
			tx.d = 0.0975
			tx.tx = 0.57375
			tx.ty = 0.06875
			square.transform = tx
			canvas.append( square )
			note.body = [canvas]
			note.containerId = "foo:bar"
			jason.addContainedObject( note )
			note_id = note.id

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']
			note = jason.getContainedObject( "foo:bar", note_id )
			canvas = note.body[0]
			assert_that( canvas, has_property( 'viewportRatio', 1.0 ) )
			square = canvas.shapeList[0]
			tx = square.transform
			assert_that(tx.a, close_to(0.05125, 0.0001))
			assert_that(tx.b, close_to(-0.04625, 0.0001))
			assert_that(tx.c, close_to(0.04625, 0.0001))
			assert_that(tx.d, close_to(0.05125, 0.0001))
			assert_that(tx.tx, close_to(0.57375, 0.0001))
			assert_that(tx.ty, close_to(0.06875, 0.0001))
