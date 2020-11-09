#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IRequest

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.interfaces import ISite

from nti.appserver.brand.utils import get_site_brand_name

from nti.appserver.policies.site_policies import guess_site_display_name


@component.adapter(ISite, IRequest)
@interface.implementer(IDisplayNameGenerator)
class _SiteNameGenerator(object):

    def __init__(self, site, request):
        self.request = request
        self.site = site

    @Lazy
    def _displayName(self):
        site_manager = self.site.getSiteManager()
        display_name = get_site_brand_name(site_manager)
        if display_name:
            display_name = display_name.strip()
        else:
            display_name = guess_site_display_name(self.request)
        return display_name

    def __call__(self):
        return self._displayName