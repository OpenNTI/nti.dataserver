#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import inspect

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope.dottedname import resolve as dottedname

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.asynchronous.interfaces import IBaseQueue

from nti.asynchronous.scheduled.job import create_scheduled_job
from nti.asynchronous.scheduled.job import ScheduledJob

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import StandardExternalFields

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             context=IBaseQueue,
             request_method='POST',
             permission=nauth.ACT_NTI_ADMIN,
             renderer='rest')
class ScheduledQueuePOSTView(AbstractAuthenticatedView,
                             ModeledContentUploadRequestUtilsMixin):

    def performReadCreateUpdateContentObject(self, user, search_owner=False, externalValue=None,
                                             deepCopy=False, add_to_connection=True):
        # Don't add to the connection
        return super(ScheduledQueuePOSTView, self).performReadCreateUpdateContentObject(user,
                                                                                        search_owner,
                                                                                        externalValue,
                                                                                        deepCopy,
                                                                                        add_to_connection=False)

    def createContentObject(self, user, datatype, externalValue, creator):
        # We have to override everything here because ScheduledJob has dependencies in its __init__
        # that can't be updated as a modeled object
        clazz = externalValue.get(StandardExternalFields.CLASS)
        if clazz != ScheduledJob.__name__:
            raise hexc.HTTPUnprocessableEntity(u'Class type must be "ScheduledJob" (%s provided)' % clazz)
        execution_time = externalValue.get('timestamp')  # TODO may do some checking for datetime etc to make friendlier
        job_args = externalValue.get('job_args')
        job_kwargs = externalValue.get('job_kwargs')
        job_id = externalValue.get('job_id')
        call = externalValue.get('callable')
        call = dottedname.resolve(call)

        if inspect.isclass(call):
            # Currently don't support passing init vars
            call = call()
        job = create_scheduled_job(call,
                                   execution_time,
                                   jargs=job_args,
                                   jkwargs=job_kwargs,
                                   jobid=job_id)
        return job

    def __call__(self, *args, **kwargs):
        job = self.readCreateUpdateContentObject(self.remoteUser)
        self.context.put(job)
        return job
