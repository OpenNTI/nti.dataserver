#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)



from hamcrest import assert_that, is_, not_none, has_entry
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
		user = User.create_user( self.ds, username='jason.madden@nextthought.com' )

		change = Change( Change.CIRCLED, user )

		assert_that( change, validly_provides(IStreamChangeCircledEvent))


	@WithMockDSTrans
	def test_to_external(self):
		user = User.create_user( self.ds, username='jason.madden@nextthought.com' )

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
