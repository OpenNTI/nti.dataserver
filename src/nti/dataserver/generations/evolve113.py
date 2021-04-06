#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from zope.component.interfaces import ISite

from zope.interface.interfaces import IComponents
from zope.interface.interfaces import IAdapterRegistry

from zope.generations.utility import findObjectsMatching

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.interfaces import IOIDResolver

logger = __import__('logging').getLogger(__name__)

generation = 113


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
        def condition(obj):
            return ISite.providedBy(obj) or IAdapterRegistry.providedBy(obj) or IComponents.providedBy(obj)

        for thing in findObjectsMatching(conn.root(), condition):
            if ISite.providedBy(thing):
                thing = thing.getSiteManager()
            if hasattr(thing, 'rebuild'):
                thing.rebuild()
                seen.add(thing.utilities)
                seen.add(thing.adapters)
                continue
            if IComponents.providedBy(thing):
                regs = thing.utilities, thing.adapters
            else:
                assert IAdapterRegistry.providedBy(thing)
                regs = (thing,)
            for reg in regs:
                if reg in seen:
                    continue
                seen.add(reg)
                reg.rebuild()
                conn.cacheGC() # keep memory from blowing up
            if len(seen) % 100 == 0:
                logger.info("Rebuilt %s registries", len(seen))
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 113 by rebuilding registry sub types.
    """
    do_evolve(context, generation)
