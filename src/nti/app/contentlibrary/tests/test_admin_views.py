#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import empty

from nti.app.testing.application_webtest import ApplicationLayerTest
from . import ContentLibraryApplicationTestLayer
from nti.app.testing.decorators import WithSharedApplicationMockDS

from zope.component import eventtesting
from zope.interface.interfaces import IRegistered
from nti.contentlibrary.interfaces import IContentPackageLibraryModifiedOnSyncEvent

class TestApplicationAdminViews(ApplicationLayerTest):

	layer = ContentLibraryApplicationTestLayer

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_sync_all_libraries(self):
		href = '/dataserver2/@@SyncAllLibraries'

		eventtesting.clearEvents()

		self.testapp.post(href)

		# We're outside the transaction now, but we can check
		# that we got some events. We would have done ObjectAdded
		# for all the new site libraries for the first time, plus
		# the Will/Modified/DidSync events...
		# XXX: NOTE: We depend on having some of the nti.app.sites
		# packages installed at test time for this to work.

		regs = eventtesting.getEvents(IRegistered)
		assert_that( regs, is_not(empty()))

		syncd = eventtesting.getEvents(IContentPackageLibraryModifiedOnSyncEvent)
		assert_that( syncd, is_not(empty()))
