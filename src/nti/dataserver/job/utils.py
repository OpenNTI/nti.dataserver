#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.asynchronous.scheduled.job import create_scheduled_job

from nti.asynchronous.scheduled.utils import add_scheduled_job

from nti.dataserver.job.interfaces import IScheduledJob

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def create_and_queue_scheduled_job(obj):
    job = IScheduledJob(obj, None)
    if job is None:
        logger.debug(u'No scheduled job implementation for %s' % obj)
        return
    job = create_scheduled_job(job,
                               jobid=job.job_id,
                               timestamp=job.execution_time,
                               jargs=job.job_args,
                               jkwargs=job.job_kwargs)
    return add_scheduled_job(job)
