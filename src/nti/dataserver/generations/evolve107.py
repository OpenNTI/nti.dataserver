#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users.utils import get_communities_by_site

from nti.site import get_all_host_sites

logger = __import__('logging').getLogger(__name__)

generation = 107


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warning("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator)
        return None


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    total_count = 0
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"
        seen = set()
        sites = get_all_host_sites()
        for site in sites:
            with current_site(site):
                site_communities = get_communities_by_site()
                for site_community in site_communities or ():
                    if site_community is None:
                        continue
                    username = site_community.username
                    if username in seen:
                        continue
                    seen.add(username)
                    old_member_count = site_community.number_of_members()
                    missing_wrefs = [x for x in site_community._members if x() is None]
                    if missing_wrefs:
                        total_count += len(missing_wrefs)
                        for missing_wref in missing_wrefs:
                            site_community._del_member(missing_wref)

                        logger.info("Cleaned up community members (%s) (removed=%s) (old=%s) (new=%s)",
                                    site_community.username,
                                    len(missing_wrefs),
                                    old_member_count,
                                    site_community.number_of_members())
    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done (%s users removed from communities).',
                generation,
                total_count)


def evolve(context):
    """
    Evolve to generation 106 by moving site communities to regular
    communities with the default auto-subscribe.
    """
    do_evolve(context, generation)

