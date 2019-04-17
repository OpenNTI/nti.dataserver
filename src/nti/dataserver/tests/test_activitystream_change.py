#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import division

from __future__ import absolute_import

from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
does_not = is_not

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer, WithMockDSTrans

import unittest

from nti.dataserver.activitystream_change import Change
from nti.dataserver.users import User
from nti.externalization.externalization import toExternalObject
from nti.dataserver.interfaces import IStreamChangeCircledEvent
from nti.testing.matchers import validly_provides

class TestChange(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@WithMockDSTrans
	def test_dynamic_provides(self):
		user = User.create_user(self.ds, username=u'jason.madden@nextthought.com')

		change = Change(Change.CIRCLED, user)

		assert_that(change, validly_provides(IStreamChangeCircledEvent))

		change2 = Change(Change.CREATED, user)
		assert_that(change2, does_not(validly_provides(IStreamChangeCircledEvent)))
		assert_that(change, validly_provides(IStreamChangeCircledEvent))

		change2.type = Change.CIRCLED
		assert_that(change2, validly_provides(IStreamChangeCircledEvent))


	@WithMockDSTrans
	def test_to_external(self):
		user = User.create_user( self.ds, username=u'jason.madden@nextthought.com' )

		change = Change( Change.CIRCLED, user )
		assert_that( change.object, is_( user ) )
		assert_that( str(change), is_(repr(change)) )

		# Non summary
		ext_obj = toExternalObject( change )
		assert_that( ext_obj, has_entry( 'Item', not_none() ) )

		# Summary
		change.useSummaryExternalObject = True
		ext_obj = toExternalObject( change )
		assert_that( ext_obj, has_entry( 'Item', not_none() ) )
