#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from datetime import datetime

from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.schema.fieldproperty import createFieldProperties

from nti.asynchronous.scheduled.job import create_scheduled_job

from nti.asynchronous.scheduled.utils import add_scheduled_job

from nti.dataserver.job.interfaces import IJob
from nti.dataserver.job.interfaces import IScheduledJob

from nti.ntiids.oids import to_external_ntiid_oid

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IJob)
class AbstractEmailJob(object):

    createFieldProperties(IJob)

    def __init__(self, obj):
        # We don't want to store this obj in the job instance because it messes up pickling
        obj_ntiid = to_external_ntiid_oid(obj)
        if obj_ntiid is None:
            raise ValueError(u'Unable to create an email job for an object without an ntiid')
        self.job_kwargs['obj_ntiid'] = obj_ntiid

    @property
    def utc_now(self):
        epoch = datetime.utcfromtimestamp(0)
        now_datetime = datetime.utcnow()
        time_delta = now_datetime - epoch
        return time_delta.total_seconds()

    @Lazy
    def job_kwargs(self):
        return {}

    @Lazy
    def job_args(self):
        return []

    @Lazy
    def job_id(self):
        return '%s_added_%s' % (self.job_id_prefix, self.utc_now)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


def create_and_queue_scheduled_email_job(obj):
    job = IScheduledJob(obj, None)
    if job is None:
        logger.debug(u'No scheduled email job implementation for %s' % obj)
        return
    job = create_scheduled_job(job,
                               jobid=job.job_id,
                               timestamp=job.execution_time,
                               jargs=job.job_args,
                               jkwargs=job.job_kwargs)
    return add_scheduled_job(job)
