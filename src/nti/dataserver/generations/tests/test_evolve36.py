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
from hamcrest import has_item


from nti.dataserver.generations.evolve36 import evolve

import nti.testing.base
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.common.deprecated import hides_warnings
from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture



class TestEvolve36(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve36(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			#install( context )
			owner_user, member_user, _member_user2, parent_dfl = _dfl_sharing_fixture( self.ds )

			# Now, if we cheat and remove the member from the DFL, but leave the relationship
			# in place, then we handle that
			parent_dfl.removeFriend( member_user )
			member_user.record_dynamic_membership( parent_dfl )
			member_user.follow( parent_dfl )
			assert_that( list(parent_dfl), does_not( has_item( member_user ) ) )
			assert_that( list(member_user.dynamic_memberships), has_item( parent_dfl ) )
			assert_that( list(member_user.entities_followed), is_( [parent_dfl] ))

		def check_changed(context, owner_user=owner_user, member_user=member_user):
			ds_folder = context.connection.root()['nti.dataserver']
			owner_user = ds_folder['users'][owner_user.username]
			member_user = ds_folder['users'][member_user.username]
			everyone = ds_folder['users']['Everyone']

			assert_that( list( member_user.entities_followed), is_( [] ) )
			assert_that( list( member_user.dynamic_memberships ), is_( [everyone] ) )

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			# XXX Fails on pypy. something is getting lost in the commit for JUST
			# the dynamic_memberships object
			check_changed(context)
