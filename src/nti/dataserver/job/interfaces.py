#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.schema import Dict
from zope.schema import List

from nti.schema.field import Number
from nti.schema.field import ValidTextLine

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class IEmailJob(interface.Interface):
    """
    A callable for an asynchronous job that sends an email with
    the appropriate metadata for registering the job
    """

    job_id = ValidTextLine(title=u'Job ID',
                           description=u'The id that will be registered for this job',
                           required=True)

    job_id_prefix = ValidTextLine(title=u'Job ID Prefix',
                                  description=u'The prefix for this job',
                                  required=True,
                                  default=u'EmailJob')

    job_args = List(title=u'Job Args',
                    description=u'Args that will be passed to the job callable',
                    required=False)

    job_kwargs = Dict(title=u'Job Kwargs',
                      description=u'Kwargs that will be passed to the job callable',
                      required=False)


class IScheduledEmailJob(IEmailJob):
    """
    An IEmailJob that will be ran as a scheduled job
    """

    execution_time = Number(title=u'Execution Time',
                            description=u'The timestamp at which this object should be executed',
                            required=True)

    execution_buffer = Number(title=u'Execution Buffer',
                              description=u'The amount of time to buffer from when this job is queued to execution',
                              required=True)
