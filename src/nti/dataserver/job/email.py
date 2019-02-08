#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import calendar

from zope import datetime
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.asynchronous.scheduled.job import create_scheduled_job

from nti.asynchronous.scheduled.utils import add_scheduled_job

from nti.dataserver.job.interfaces import IEmailJob

from nti.dataserver.job.interfaces import IScheduledEmailJob

from nti.schema.fieldproperty import createDirectFieldProperties

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IEmailJob)
class AbstractEmailJob(object):

    createDirectFieldProperties(IEmailJob)

    def __init__(self, obj):
        self.obj = obj

    @Lazy
    def job_id(self):
        return '%s_added_%s' % (self.job_id_prefix, calendar.timegm(datetime.utcnow()))

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


@interface.implementer(IScheduledEmailJob)
class ScheduledEmailJobMixin(object):

    execution_buffer = 0

    @Lazy
    def execution_time(self):
        return calendar.timegm(datetime.utcnow()) + self.execution_buffer


def create_and_queue_scheduled_email_job(obj):
    job = IScheduledEmailJob(obj, None)
    if job is None:
        logger.debug(u'No scheduled email job implementation for %s' % obj)
        return
    job = create_scheduled_job(job,
                               jobid=job.job_id,
                               timestamp=job.execution_time,
                               jargs=job.job_args,
                               jkwargs=job.job_kwargs)
    return add_scheduled_job(job)
