#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import contains

from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve28 import evolve

from zope.catalog.interfaces import ICatalog
from zope import component

import nti.tests
import nti.dataserver
from nti.dataserver import users
from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings


class TestEvolve30(mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve30(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=10,skip_passwords=True).install( context )


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )


		with mock_db_trans( ) as conn:
			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )
			ent_catalog = component.getUtility(ICatalog, name='nti.dataserver.++etc++entity-catalog')

			results = list(ent_catalog.searchResults( email=('Jason.madden@nextthought.com','jason.madden@nextthought.com') ))
			assert_that( results, contains( jason ) )
