#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.site import get_host_site

from zope.component.hooks import site as current_site

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def RunJobInSite(method):
    from functools import wraps

    @wraps(method)
    def run_job_in_site(self, *args, **kwargs):
        site_name = self.job_kwargs.get('site_name')
        site = get_host_site(site_name)
        with current_site(site):
            return method(self, *args, **kwargs)
    return run_job_in_site

