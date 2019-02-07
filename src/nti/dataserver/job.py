#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import time

from zope import interface

from nti.asynchronous.scheduled.job import create_scheduled_job

from nti.asynchronous.scheduled.utils import add_scheduled_job

from nti.dataserver.interfaces import IEmailJob

from nti.dataserver.interfaces import IScheduledEmailJob

from nti.schema.fieldproperty import createDirectFieldProperties

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IEmailJob)
class AbstractEmailJob(object):

    createDirectFieldProperties(IEmailJob)

    _jid = None

    @property
    def jid(self):
        if self._jid is None:
            self._jid = '%s_added_%s' % (self.jid_prefix, time.time())
        return self._jid

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


@interface.implementer(IScheduledEmailJob)
class ScheduledEmailJobMixin(object):

    _execution_time = None
    execution_buffer = None

    @property
    def execution_time(self):
        if self._execution_time is None:
            self._execution_time = time.time() + self.execution_buffer
        return self._execution_time


def create_and_queue_scheduled_email_job(obj):
    job = IScheduledEmailJob(obj, None)
    if job is None:
        logger.debug(u'No scheduled email job implementation for %s' % obj)
        return
    job = create_scheduled_job(job,
                               jobid=job.jid,
                               timestamp=job.execution_time,
                               jargs=job.jargs,
                               jkwargs=job.jkwargs)
    return add_scheduled_job(job)
