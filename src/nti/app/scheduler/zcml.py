#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import ast

from nti.schema.field import Number, ListOrTuple, ValidTextLine
from zope import interface
from zope.configuration.fields import GlobalObject
from zope.schema import Dict
from zope.schema._bootstrapinterfaces import IFromUnicode

from nti.asynchronous.scheduled.job import create_scheduled_job
from nti.asynchronous.scheduled.utils import add_scheduled_job

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IFromUnicode)
class FromUnicodeDict(Dict):

    def fromUnicode(self, value):
        result = ast.literal_eval(value)
        return result


class ICreateScheduledJob(interface.Interface):

    callable = GlobalObject(title=u'Callable',
                            description=u'The callable this job should execute',
                            required=True)

    timestamp = Number(title=u'Execution timestamp',
                       description=u'The timestamp for when this job should execute',
                       default=0,
                       required=False)

    job_args = ListOrTuple(title=u'Job Args',
                           description=u'The args that will be passed to this callable',
                           required=False,
                           value_type=ValidTextLine())

    job_kwargs = FromUnicodeDict(title=u'Job Kwargs',
                                 description=u'The kwargs that will be passed to this callable',
                                 key_type=ValidTextLine(),
                                 value_type=ValidTextLine(),
                                 required=False)

    job_id = ValidTextLine(title=u'Job ID',
                           description=u'The ID for this job.',
                           required=False)


def createScheduledJob(_context,
                       callable,
                       timestamp=0,  # Ensures this job is always executed
                       job_args=None,
                       job_kwargs=None,
                       job_id=None):
    job = create_scheduled_job(callable,
                               timestamp,
                               jargs=job_args,
                               jkwargs=job_kwargs,
                               jobid=job_id)
    add_scheduled_job(job)
