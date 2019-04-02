#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from datetime import datetime

from pyramid.request import Request

from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request

from webob.request import environ_from_url

from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.schema.fieldproperty import createFieldProperties

from nti.dataserver.job.interfaces import IJob

from nti.ntiids.oids import to_external_ntiid_oid

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IJob)
class AbstractJob(object):

    createFieldProperties(IJob)

    def __init__(self, obj):
        # We don't want to store this obj in the job instance because it messes up pickling
        obj_ntiid = to_external_ntiid_oid(obj)
        site_name = getSite().__name__
        if obj_ntiid is None:
            raise ValueError(u'Unable to create a job for an object without an ntiid')
        self.job_kwargs['obj_ntiid'] = obj_ntiid
        self.job_kwargs['site_name'] = site_name

    def get_request(self, context, application_url=None):
        request = get_current_request()
        if request is None:
            environ = {}
            if application_url:
                environ = environ_from_url(application_url)
            # fake a request
            request = Request(environ=environ)
            request.context = context
            request.registry = get_current_registry()
        return request

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
