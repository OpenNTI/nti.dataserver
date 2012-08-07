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

from zope import component
from zope.intid import interfaces as intid_interfaces

from nti.tests import verifiably_provides
from nti.tests import is_true, is_false

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import flagging
from nti.dataserver.contenttypes import Note as _Note

from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase, WithMockDSTrans

from nti.contentrange.contentrange import ContentRangeDescription
def Note():
	n = _Note()
	n.applicableRange = ContentRangeDescription()
	return n

class TestFlagging(ConfiguringTestBase):

	@WithMockDSTrans
	def test_flagging(self):
		"Notes can be flagged and unflagged"
		n = Note()
		component.getUtility( intid_interfaces.IIntIds ).register( n )

		assert_that( component.getAdapter( n, nti_interfaces.IGlobalFlagStorage ), verifiably_provides( nti_interfaces.IGlobalFlagStorage ) )

		# first time does something
		assert_that( flagging.flag_object( n, 'foo@bar' ), is_( none() ) )
		# second time no-op
		assert_that( flagging.flag_object( n, 'foo@bar' ), is_( none() ) )

		assert_that( flagging.flags_object( n, 'foo@bar' ), is_true() )

		# first time does something
		assert_that( flagging.unflag_object( n, 'foo@bar' ), is_( none() ) )
		# second time no-op
		assert_that( flagging.unflag_object( n, 'foo@bar' ), is_( none() ) )

		assert_that( flagging.flags_object( n, 'foo@bar' ), is_false() )

		# If we unregister while flagged, the flagging status changes
		assert_that( flagging.flag_object( n, 'foo@bar' ), is_( none() ) )
		component.getUtility( intid_interfaces.IIntIds ).unregister( n )

		assert_that( flagging.flags_object( n, 'foo@bar' ), is_false() )
