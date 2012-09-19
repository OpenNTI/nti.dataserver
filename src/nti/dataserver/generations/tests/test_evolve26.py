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
from hamcrest import is_not as does_not
from hamcrest import has_key


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve26 import evolve


from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas, CanvasUrlShape, NonpersistentCanvasUrlShape

import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings



class TestEvolve26(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve26(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			jason.streamCache.__name__ = None
			jason.streamCache.__parent__ = None


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']

			assert_that( jason.streamCache, has_property( '__name__', 'streamCache' ) )

			# Lazy objects weren't created
			jeff = ds_folder['users']['jeff.muehring@nextthought.com']
			jeff._p_activate()
			assert_that( jeff.__dict__, does_not( has_key( 'streamCache' ) ) )
