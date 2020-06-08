#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.dataserver.metadata import get_metadata_catalog
from nti.dataserver.metadata.index import IX_MENTIONED
from nti.dataserver.metadata.index import MentionedIndex
from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from zope.intid import IIntIds

from zope.location.location import locate

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

logger = __import__('logging').getLogger(__name__)

generation = 110


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
    try:
        with current_site(ds_folder):
            assert component.getSiteManager() == ds_folder.getSiteManager(), \
                   "Hooks not installed?"
            lsm = ds_folder.getSiteManager()
            intids = lsm.getUtility(IIntIds)

            catalog = get_metadata_catalog()
            if IX_MENTIONED not in catalog:
                index = MentionedIndex(family=intids.family)
                intids.register(index)
                locate(index, catalog, IX_MENTIONED)
                catalog[IX_MENTIONED] = index

                catalog.updateIndexes()
    finally:
        component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)

    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 110 by adding an mentioned index
    to the metadata catalog
    """
    do_evolve(context, generation)
