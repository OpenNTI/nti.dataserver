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

from zope.location.location import locate

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.coremetadata.interfaces import IX_LASTSEEN_TIME

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import get_entity_catalog

generation = 114

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warning(
                "Using dataserver without a proper ISiteManager."
            )
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation): # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
                "Hooks not installed?"
        entity_catalog = get_entity_catalog()
        metadata_catalog = get_metadata_catalog()
        try:
            lastseen_index = entity_catalog[IX_LASTSEEN_TIME]
        except KeyError:
            pass
        else:
            if IX_LASTSEEN_TIME not in metadata_catalog:
                locate(lastseen_index, metadata_catalog, IX_LASTSEEN_TIME)
                metadata_catalog[IX_LASTSEEN_TIME] = lastseen_index
        assert IX_LASTSEEN_TIME in metadata_catalog

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 114 by moving the last seen index from the inlined
    entity catalog to the metadata catalog.
    """
    do_evolve(context, generation)
