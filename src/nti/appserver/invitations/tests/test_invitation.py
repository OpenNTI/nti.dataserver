#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that

from hamcrest import has_property
from hamcrest import contains

from nti.testing.matchers import verifiably_provides

from .. import interfaces

from .. import invitation


from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from zope.component import eventtesting

class TestInvitation(DataserverLayerTest):
	def test_valid_interface(self):

		assert_that( invitation.PersistentInvitation(), verifiably_provides( interfaces.IInvitation ) )

	def test_accept_event(self):
		eventtesting.clearEvents()

		invite = invitation.PersistentInvitation()
		invite.accept( invite )

		assert_that( eventtesting.getEvents( interfaces.IInvitationAcceptedEvent ),
					 contains( has_property( 'object', invite ) ) )
