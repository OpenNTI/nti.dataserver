#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.generations.evolve21 import evolve


import nti.tests
from nti.tests import verifiably_provides

import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import z3c.password.interfaces
import persistent.interfaces

import fudge


class TestEvolve21(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@WithMockDS
	def test_evolve21(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ds_folder = context.connection.root()['nti.dataserver']
			ds_folder.getSiteManager().unregisterUtility( provided=z3c.password.interfaces.IPasswordUtility )


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			assert_that( ds_folder.getSiteManager().getUtility( z3c.password.interfaces.IPasswordUtility ),
						 verifiably_provides( z3c.password.interfaces.IPasswordUtility ) )
			assert_that( ds_folder.getSiteManager().getUtility( z3c.password.interfaces.IPasswordUtility ),
						 verifiably_provides( persistent.interfaces.IPersistent ) )
