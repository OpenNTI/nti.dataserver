#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import instance_of
from hamcrest import has_entry


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve27 import evolve


from nti.dataserver.contenttypes import Note
from nti.dataserver import activitystream_change

import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings
import persistent


class TestEvolve27(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve27(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			note = Note()
			note.body = ["stuff in the body"]
			note.containerId = "foo:bar"
			jason.addContainedObject( note )
			note_id = note.id

			change = activitystream_change.Change( activitystream_change.Change.CREATED, note )
			change.__dict__['creator'] = jason

			jeff = ds_folder['users']['jeff.muehring@nextthought.com']
			jeff._addToStream( change )

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		# OK, at this point it should be a weak reference in the change object.
		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jeff = ds_folder['users']['jeff.muehring@nextthought.com']
			jason = ds_folder['users']['jason.madden@nextthought.com']

			change = jeff.getContainedStream( 'foo:bar' )[0]
			assert_that( change.__dict__, has_entry( 'creator', instance_of( persistent.wref.WeakRef ) ) )
			assert_that( change.creator, is_( jason ) )


			# Unfortunately, testing the 'removed user' branch is hard, because
			# the events that fire prevent that situation from arising now
