#!/usr/bin/env python2.7

import unittest
from hamcrest import assert_that, is_, not_none, has_entry
from nti.dataserver.tests import has_attr, provides
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase, WithMockDSTrans
from nti.tests import verifiably_provides

from zope.interface.verify import verifyObject
from zope import component

from nti.dataserver import datastructures
from nti.dataserver.activitystream_change import Change
from nti.dataserver.users import User

class TestChange(ConfiguringTestBase):

	@WithMockDSTrans
	def test_to_external(self):
		user = User( 'jason.madden@nextthought.com' )

		change = Change( Change.CIRCLED, user )
		assert_that( change.object, is_( user ) )
		assert_that( str(change), is_(repr(change)) )

		# Non summary
		ext_obj = datastructures.toExternalObject( change )
		assert_that( ext_obj, has_entry( 'Item', not_none() ) )

		# Summary
		change.useSummaryExternalObject = True
		ext_obj = datastructures.toExternalObject( change )
		assert_that( ext_obj, has_entry( 'Item', not_none() ) )
