#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: test_evolve32.py 12983 2012-10-08 15:35:51Z jason.madden $
"""
from __future__ import print_function, unicode_literals

import fudge

import nti.dataserver
from nti.dataserver.generations.evolve32 import evolve
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas, CanvasCircleShape

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.deprecated import hides_warnings

from hamcrest import (assert_that,  has_property)

class TestEvolve32(mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve32(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )

			note = Note()
			canvas = Canvas()
			delattr(canvas, 'viewPortRatio')
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
			canvas = note.body[0]
			assert_that( canvas, has_property( 'viewPortRatio', 1.0 ) )
