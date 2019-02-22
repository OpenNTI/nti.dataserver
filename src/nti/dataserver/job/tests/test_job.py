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

from z3c.baseregistry.baseregistry import BaseComponents

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component import globalSiteManager as BASE

from zope.component.hooks import getSite

from zope.interface.interfaces import IComponents

from nti.appserver.policies.sites import BASEADULT

from nti.coremetadata.interfaces import IUser

from nti.dataserver.job.decorators import RunJobInSite

from nti.dataserver.job.interfaces import IScheduledJob

from nti.dataserver.job.job import AbstractJob

from nti.dataserver.job.utils import create_and_queue_scheduled_job

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDS

from nti.dataserver.users import User

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class MockScheduledEmailJob(AbstractJob):

    execution_buffer = 5  # seconds

    @Lazy
    def execution_time(self):
        return self.utc_now + self.execution_buffer

    @RunJobInSite
    def __call__(self, *args, **kwargs):
        return getSite().__name__


ALPHA = BaseComponents(BASEADULT,
                       name='alpha.nextthought.com',
                       bases=(BASEADULT,))


class TestJob(DataserverLayerTest):

    layer = SharedConfiguringTestLayer

    def setUp(self):
        super(TestJob, self).setUp()
        ALPHA.__init__(ALPHA.__parent__, name=ALPHA.__name__, bases=ALPHA.__bases__)
        BASE.registerUtility(ALPHA, name=ALPHA.__name__, provided=IComponents)

    def tearDown(self):
        BASE.unregisterUtility(ALPHA, name=ALPHA.__name__, provided=IComponents)
        super(DataserverLayerTest, self).tearDown()

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
    @WithMockDS
    def test_enqueue_job(self, fake_queue):
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            queue = self._setup_mock_email_job(fake_queue)
            user = User.create_user(username=u'emailer@job.com')
            create_and_queue_scheduled_job(user)
            assert_that(queue.empty(), is_not(True))
            job = queue.get()
            assert_that(job(), is_('alpha.nextthought.com'))
