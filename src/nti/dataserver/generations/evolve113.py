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


def _rebuild(obj, seen):
    if ISite.providedBy(obj):
        obj = obj.getSiteManager()
    if hasattr(obj, 'rebuild'):
        obj.rebuild()
        seen.add(obj.utilities)
        seen.add(obj.adapters)
        return
    if IComponents.providedBy(obj):
        regs = obj.utilities, obj.adapters
    else:
        assert IAdapterRegistry.providedBy(obj)
        regs = (obj,)
    for reg in regs:
        if reg in seen:
            continue
        seen.add(reg)
        reg.rebuild()


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

        _rebuild(ds_folder, seen)
        for folder_name, sub_folder in ds_folder.items():
            if folder_name == u'Users':
                continue

            for thing in findObjectsMatching(sub_folder, condition):
                _rebuild(thing, seen)
                conn.cacheGC() # keep memory from blowing up
                if len(seen) % 100 == 0:
                    logger.info("Rebuilt %s registries", len(seen))
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 113 by rebuilding registry sub types.
    """
    do_evolve(context, generation)
