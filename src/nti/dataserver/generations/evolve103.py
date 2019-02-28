#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 103

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from nti.coremetadata.interfaces import IX_INVALID_EMAIL
from nti.coremetadata.interfaces import IUser

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users.index import EmailInvalidExtentFilteredSet
from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import install_entity_catalog


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


def do_evolve(context, generation=generation):
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
        topics = catalog[IX_TOPICS]
        try:
            topics[IX_INVALID_EMAIL]
        except KeyError:
            the_filter = EmailInvalidExtentFilteredSet(IX_INVALID_EMAIL,
                                                       family=intids.family)
            topics.addFilter(the_filter)

            _users = ds_folder['users']
            for entity in _users.values():
                if IUser.providedBy(entity):
                    doc_id = intids.queryId(entity)
                    if doc_id is not None:
                        catalog.index_doc(doc_id, entity)
                        count += 1

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s object(s) indexed', generation, count)


def evolve(context):
    """
    Evolve to generation 103 by adding "invalid email" filter set index
    """
    do_evolve(context, generation)
