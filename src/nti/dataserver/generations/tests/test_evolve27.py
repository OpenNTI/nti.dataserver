#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_entry

from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve27 import evolve


from nti.dataserver.contenttypes import Note
from nti.dataserver import activitystream_change
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

import nti.tests
from nti.tests import verifiably_provides
import nti.dataserver

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings



class TestEvolve27(mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve27(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )

			note = Note()
			note.body = ["stuff in the body"]
			note.containerId = "foo:bar"
			jason.addContainedObject( note )
			note_id = note.id

			change = activitystream_change.Change( activitystream_change.Change.CREATED, note )
			change.__dict__['creator'] = jason

			jeff = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jeff.muehring@nextthought.com' )
			jeff._addToStream( change )

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		# OK, at this point it should be a weak reference in the change object.
		with mock_db_trans( ) as conn:
			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )
			jeff = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jeff.muehring@nextthought.com' )


			change = jeff.getContainedStream( 'foo:bar' )[0]
			assert_that( change.__dict__, has_entry( 'creator', verifiably_provides( nti_interfaces.IWeakRef ) ) )
			assert_that( change.creator, is_( jason ) )


			# Unfortunately, testing the 'removed user' branch is hard, because
			# the events that fire prevent that situation from arising now
