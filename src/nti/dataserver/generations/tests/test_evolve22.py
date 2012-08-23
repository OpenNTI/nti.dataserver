#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals



from hamcrest import assert_that, is_


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve22 import evolve


from nti.dataserver.contenttypes import Note

import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import BTrees
import fudge

from nti.deprecated import hides_warnings



class TestEvolve22(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve22(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			jeff = ds_folder['users']['jeff.muehring@nextthought.com']
			# Give me some data to migrate over
			note = Note()
			note.containerId = "foo:bar"
			jason.addContainedObject( note )
			note._sharingTargets = ["baz@bas", jeff.username]
			note_id = note.id



		with mock_db_trans(  ) as conn:

			context = fudge.Fake().has_attr( connection=conn )


			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			jeff = ds_folder['users']['jeff.muehring@nextthought.com']
			note = jason.getContainedObject( "foo:bar", note_id )
			assert_that( note._sharingTargets, is_( BTrees.family64.II.TreeSet ) )

			assert_that( set(note.sharingTargets), is_( set([jeff]) ) )
