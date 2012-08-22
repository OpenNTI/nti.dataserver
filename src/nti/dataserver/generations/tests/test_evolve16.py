#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals



from hamcrest import assert_that, has_property


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve16 import evolve


from nti.dataserver.contenttypes import Note
from nti.dataserver import enclosures

import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS


import fudge

from nti.deprecated import hides_warnings



class TestEvolve16(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve16(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			# Give me some data to migrate over
			note = Note()
			note.containerId = "foo:bar"
			enclosure = enclosures.SimplePersistentEnclosure(
				'Note',
				note,
				'text/plain' )
			#jason.friendsLists['Everyone'].add_enclosure( enclosure )
			#jason.friendsLists['Everyone']._enclosures.__name__ = None
			note_id = note.id



		with mock_db_trans(  ) as conn:

			context = fudge.Fake().has_attr( connection=conn )


			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			#assert_that( jason.friendsLists['Everyone'], has_property( '_enclosures', has_property( '__name__', '++adapter++enclosures' ) ) )
