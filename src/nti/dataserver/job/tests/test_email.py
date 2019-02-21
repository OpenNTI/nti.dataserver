#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import fudge

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not

from Queue import Queue

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from nti.coremetadata.interfaces import IUser

from nti.dataserver.job.decorators import RunJobInSite

from nti.dataserver.job.interfaces import IScheduledJob

from nti.dataserver.job.email import AbstractEmailJob
from nti.dataserver.job.email import create_and_queue_scheduled_email_job

from nti.dataserver.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class MockScheduledEmailJob(AbstractEmailJob):

    execution_buffer = 5  # seconds

    @Lazy
    def execution_time(self):
        return self.utc_now + self.execution_buffer

    @RunJobInSite
    def __call__(self, *args, **kwargs):
        return getSite().__name__


class TestJob(DataserverLayerTest):

    layer = SharedConfiguringTestLayer

    def _setup_mock_email_job(self, fake_queue):
        queue = Queue()
        fake_queue.is_callable().returns(queue)

        assert_that(queue.empty(), is_(True))

        gsm = component.getGlobalSiteManager()
        gsm.registerAdapter(MockScheduledEmailJob,
                            provided=IScheduledJob,
                            required=(IUser,))  # User is arbitrary here
        return queue

    @fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
    @WithMockDSTrans
    def test_enqueue_job(self, fake_queue):
        queue = self._setup_mock_email_job(fake_queue)
        user = User.create_user(self.ds, username=u'emailer@job.com')
        create_and_queue_scheduled_email_job(user)
        assert_that(queue.empty(), is_not(True))
        job = queue.get()
        assert_that(job(), is_('dataserver2'))
