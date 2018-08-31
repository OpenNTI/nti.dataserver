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

from zope.intid.interfaces import IIntIds

from zope.location.location import locate

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users.index import IX_USERNAME
from nti.dataserver.users.index import UsernameIndex
from nti.dataserver.users.index import install_entity_catalog

generation = 98

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

    count = 0
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        catalog = install_entity_catalog(ds_folder, intids)
        if IX_USERNAME not in catalog:
            index = UsernameIndex(family=intids.family)
            intids.register(index)
            locate(index, catalog, IX_USERNAME)
            catalog[IX_USERNAME] = index

            users = ds_folder['users']
            for entity in users.values():
                doc_id = intids.queryId(entity)
                if doc_id is not None:
                    index.index_doc(doc_id, entity)
                    count += 1

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s object(s) indexed', generation, count)


def evolve(context):
    """
    Evolve to generation 98 by adding the "username" index
    """
    do_evolve(context, generation)
