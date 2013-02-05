#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)



from hamcrest import assert_that, is_, not_none, has_entry
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase, WithMockDSTrans


from zope.interface.verify import verifyObject
from zope import component


from nti.dataserver.activitystream_change import Change
from nti.dataserver.users import User
from nti.externalization.externalization import toExternalObject

class TestChange(SharedConfiguringTestBase):

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
