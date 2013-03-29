#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import contains
from hamcrest import has_length

from zope import component
from zope.intid import interfaces as intid_interfaces
from zope.component import eventtesting
import time

from nti.tests import validly_provides as verifiably_provides
from nti.tests import is_true, is_false
from nti.tests import time_monotonically_increases

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import flagging
from nti.dataserver.contenttypes import Note as _Note

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase, WithMockDSTrans

from nti.contentrange.contentrange import ContentRangeDescription
def Note():
	n = _Note()
	n.applicableRange = ContentRangeDescription()
	return n

class TestFlagging(SharedConfiguringTestBase):

	@WithMockDSTrans
	@time_monotonically_increases
	def test_flagging(self):
		"Notes can be flagged and unflagged"
		n = Note()
		component.getUtility( intid_interfaces.IIntIds ).register( n )

		assert_that( component.getAdapter( n, nti_interfaces.IGlobalFlagStorage ), verifiably_provides( nti_interfaces.IGlobalFlagStorage ) )
		eventtesting.clearEvents()

		# first time does something
		n.lastModified = 0
		now = time.time()
		assert_that( flagging.flag_object( n, 'foo@bar' ), is_( none() ) )
		# second time no-op
		assert_that( flagging.flag_object( n, 'foo@bar' ), is_( none() ) )

		# Fired one event
		assert_that( eventtesting.getEvents(nti_interfaces.IObjectFlaggedEvent), has_length(1) )
		# Updated time once
		assert_that( n.lastModified, is_( now + 1 ) )
		n.lastModified = 0

		assert_that( flagging.flags_object( n, 'foo@bar' ), is_true() )
		assert_that( list(component.getAdapter( n, nti_interfaces.IGlobalFlagStorage ).iterflagged()), contains( n ) )

		# first time does something
		assert_that( flagging.unflag_object( n, 'foo@bar' ), is_( none() ) )
		# second time no-op
		assert_that( flagging.unflag_object( n, 'foo@bar' ), is_( none() ) )
		# Fired one event
		assert_that( eventtesting.getEvents(nti_interfaces.IObjectUnflaggedEvent), has_length(1) )
		# updated time once
		assert_that( n.lastModified, is_( now + 2 ) )
		assert_that( flagging.flags_object( n, 'foo@bar' ), is_false() )

		# If we unregister while flagged, the flagging status changes
		assert_that( flagging.flag_object( n, 'foo@bar' ), is_( none() ) )
		component.getUtility( intid_interfaces.IIntIds ).unregister( n )

		assert_that( flagging.flags_object( n, 'foo@bar' ), is_false() )
