#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals



from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import contains
from hamcrest import starts_with
from hamcrest import is_not as does_not
from hamcrest import has_length


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve39 import evolve

from BTrees.OOBTree import OOTreeSet


import nti.testing.base
import nti.dataserver
from nti.dataserver import users

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings
from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture
from nti.dataserver.contenttypes import Note


class TestEvolve39(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve39(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			#install( context )
			ExampleDatabaseInitializer(max_test_users=5,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']
			jason.friendsLists._SampleContainer__data.clear()
			jason.friendsLists._BTreeContainer__len.set( 0 )

			jason.friendsLists['Everyone'] = users.FriendsList('Everyone')
			jason.friendsLists['Everyone'].creator = None
			assert_that( jason.friendsLists, has_length( 1 ) )

			# add some things and break the assumption that
			# inReplyTo will already be set.
			note = Note()
			note.containerId = 'foo:bar'

			jason.addContainedObject( note )
			note_id = note.id

			note2 = Note()
			note2.containerId = note.containerId

			jason.addContainedObject( note2 )

			note2.inReplyTo = note
			assert_that( list(note.replies), is_( [] ) )


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']

			note = jason.getContainedObject( 'foo:bar', note_id )
			assert_that( list(note.replies), is_( [note2] ) )
			assert_that( list(note.referents), is_( [note2] ) )
