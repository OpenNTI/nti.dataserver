#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecated(
    "Moved to nti.site",
    _TrivialSite="nti.site.transient:TrivialSite",
    get_site_for_site_names="nti.site.site:get_site_for_site_names",
    synchronize_host_policies="nti.site.hostpolicy:synchronize_host_policies",
    run_job_in_all_host_sites="nti.site.hostpolicy:run_job_in_all_host_sites")

from zope import component

from zope import interface

from zope.securitypolicy.principalrole import PrincipalRoleManager

from nti.dataserver.interfaces import ISiteRoleManager

from nti.externalization.persistence import NoPickle


def site_role_manager(site):
    return component.queryUtility(ISiteRoleManager)


@NoPickle
@interface.implementer(ISiteRoleManager)
class SiteRoleManager(PrincipalRoleManager):
    """
    Instances of this class should be registered as utilities inside
    a site.
    """
