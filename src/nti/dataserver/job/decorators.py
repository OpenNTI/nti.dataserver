#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component

from zope.component.hooks import site as current_site

from nti.asynchronous.scheduled.job import create_scheduled_job

from nti.asynchronous.scheduled.utils import add_scheduled_job

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.job.utils import utc_now

from nti.site.site import get_site_for_site_names

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def RunJobInSite(method):
    from functools import wraps

    @wraps(method)
    def run_job_in_site(self, *args, **kwargs):
        site_name = self.job_kwargs.get('site_name')
        dataserver = component.getUtility(IDataserver)
        ds_folder = dataserver.root_folder['dataserver2']
        with current_site(ds_folder):
            job_site = get_site_for_site_names((site_name,))
        with current_site(job_site):
            return method(self, *args, **kwargs)
    return run_job_in_site


# TODO is an event based reschedule more appropriate?
def PeriodicJob(period, always_reschedule=True):
    """
    Reschedules a job according to the provided period.

    Period is expected to be an int representing the number of seconds between each execution

    If always_schedule is True the job will always be rescheduled, even if the attempted execution raised

    XXX: only supports classes as decorated functions don't survive pickling
    """
    def decorator(method):
        from functools import wraps

        @wraps(method)
        def run_job_periodically(self, *args, **kwargs):
            try:
                result = method(self, *args, **kwargs)
            except BaseException:
                if not always_reschedule:
                    raise
                else:
                    result = None
            timestamp = utc_now() + period
            # If the class has a job id defined we will give it to the new one
            new_job = create_scheduled_job(self,
                                           timestamp,
                                           jargs=args,
                                           jkwargs=kwargs,
                                           jobid=getattr(self, 'job_id', None))
            add_scheduled_job(new_job)
            return result
        return run_job_periodically
    return decorator
