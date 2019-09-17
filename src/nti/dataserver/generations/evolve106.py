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

from nti.app.users.utils import get_site_community

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users.auto_subscribe import SiteAutoSubscribeMembershipPredicate

from nti.site import get_all_host_sites

logger = __import__('logging').getLogger(__name__)

generation = 106


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

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"
        seen = set()
        sites = get_all_host_sites()
        for site in sites:
            with current_site(site):
                site_comm = get_site_community()
                if site_comm is None:
                    continue
                username = site_comm.username
                if username in seen:
                    continue
                seen.add(username)
                if site_comm is not None and site_comm.auto_subscribe is None:
                    site_comm.auto_subscribe = SiteAutoSubscribeMembershipPredicate()
                    site_comm.auto_subscribe.__parent__ = site_comm
    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 106 by moving site communities to regular
    communities with the default auto-subscribe.
    """
    do_evolve(context, generation)

