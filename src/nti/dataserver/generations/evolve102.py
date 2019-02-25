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

from zope.intid import IIntIds

from nti.app.users.utils import get_site_community

from nti.coremetadata.interfaces import IX_SITE

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users import get_entity_catalog

from nti.dataserver.users.common import entity_creation_sitename
from nti.dataserver.users.common import set_entity_creation_site

from nti.site import get_all_host_sites

logger = __import__('logging').getLogger(__name__)

generation = 102


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
        catalog = get_entity_catalog()
        site_idx = catalog[IX_SITE]
        intids = component.getUtility(IIntIds)
        sites = get_all_host_sites()
        for site in sites:
            with current_site(site):
                site_comm = get_site_community()
                if site_comm is not None:
                    creation_site = entity_creation_sitename(site_comm)
                    # Child sites can inherit a parent site community.
                    # The order of the host sites is top down as we iterate
                    # so we check to see if a creation site has already been
                    # been set in the parent to ensure it is not overwritten
                    # in the child
                    if creation_site is None:
                        site_name = site.__name__
                        set_entity_creation_site(site_comm, site_name)
                        comm_id = intids.queryId(site_comm)
                        site_idx.index_doc(comm_id, site_comm)
    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 102 by adding creation sites for site communities.
    """
    do_evolve(context, generation)

