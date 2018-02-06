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

from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver
from nti.dataserver.interfaces import ISiteCommunity

from nti.dataserver.users.communities import Community

from nti.site.hostpolicy import run_job_in_all_host_sites

generation = 94

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def mark_communities():
    policy = component.queryUtility(ISitePolicyUserEventListener)
    com_username = getattr(policy, 'COM_USERNAME', '')
    if com_username:
        result = Community.get_community(com_username)
        if result is not None:
            interface.alsoProvides(result, ISiteCommunity)


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        run_job_in_all_host_sites(mark_communities)
        component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
        logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to 94 by marking site communities explicitly.
    """
    do_evolve(context, generation)
