#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.generations.evolve55 import evolve

import fudge

from nti.common.deprecated import hides_warnings
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

class TestEvolve55(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):

	@hides_warnings
	@WithMockDS
	def test_evolve55(self):
		
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			ExampleDatabaseInitializer(max_test_users=5,skip_passwords=True).install( context )

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )
