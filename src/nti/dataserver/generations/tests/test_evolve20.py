#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_key
from hamcrest import is_not
from hamcrest import same_instance


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.generations.evolve20 import evolve



import nti.tests


import nti.dataserver
from nti.dataserver import containers
from nti.dataserver.interfaces import IShardLayout
from zope.container.contained import Contained

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS


import fudge


class TestEvolve20(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@WithMockDS
	def test_evolve20(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			install( context )
			del  conn.root()['nti.dataserver']['users']
			old_users = conn.root()['nti.dataserver']['users'] = containers.CaseInsensitiveLastModifiedBTreeContainer()
			IShardLayout( conn ).users_folder['jason'] = Contained()

			del conn.root()['nti.dataserver']['shards']


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

			assert_that( conn.root()['nti.dataserver'], has_key( 'shards' ) )
			assert_that( IShardLayout( conn ).users_folder, has_key( 'jason' ) )
			assert_that( IShardLayout(conn).users_folder, is_not( same_instance( old_users ) ) )
