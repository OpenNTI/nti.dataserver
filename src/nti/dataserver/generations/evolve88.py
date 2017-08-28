#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 88

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

ID_CATALOG_NAME = 'nti.dataserver.++etc++external-identifier-catalog'

IX_EXTERNAL_IDS = 'externalIds'


def do_evolve(context):
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    with site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)
        catalog = lsm.queryUtility(ICatalog, name=ID_CATALOG_NAME)
        if catalog is not None:
            idx = catalog[IX_EXTERNAL_IDS]
            for obj in (catalog, idx):
                if intids.queryId(obj) is not None:
                    intids.unregister(obj)
            lsm.unregisterUtility(catalog,
                                  provided=ICatalog,
                                  name=ID_CATALOG_NAME)

    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to 88 by unregistering unused catalog
    """
    do_evolve(context)
