#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.site.site import get_site_for_site_names

from zope import component

from zope.component.hooks import site as current_site

from nti.dataserver.interfaces import IDataserver

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

