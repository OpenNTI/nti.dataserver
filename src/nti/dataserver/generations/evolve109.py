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

from zope.location.location import locate

from nti.coremetadata.interfaces import IX_AFFILIATION

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users import get_entity_catalog

from nti.dataserver.users.index import AffiliationIndex

logger = __import__('logging').getLogger(__name__)

generation = 109


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
        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        catalog = get_entity_catalog()
        if IX_AFFILIATION not in catalog:
            index = AffiliationIndex(family=intids.family)
            intids.register(index)
            locate(index, catalog, IX_AFFILIATION)
            catalog[IX_AFFILIATION] = index

            users = ds_folder['users']
            for user in users.values():
                doc_id = intids.queryId(user)
                if doc_id is not None:
                    index.index_doc(doc_id, user)
    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 109 by adding an affiliation index
    """
    do_evolve(context, generation)
