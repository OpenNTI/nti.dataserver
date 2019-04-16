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
from zope.component.hooks import getSite

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.vocabularyregistry.subscribers import install_site_vocabulary_container

from nti.site.hostpolicy import run_job_in_all_host_sites

logger = __import__('logging').getLogger(__name__)


generation = 104


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


def install_vocabulary_item_container():
    site_mgr = getSite().getSiteManager()
    install_site_vocabulary_container(local_site_manager=site_mgr)


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

        run_job_in_all_host_sites(install_vocabulary_item_container)
        component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
        logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to 104 by installing vocabulary item container for every host sites.
    """
    do_evolve(context, generation)
