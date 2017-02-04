#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 33

from zope import component
from zope import interface

from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.contentsearch.interfaces import IContentSearcher

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites


def _remover(registry=component):
    result = 0
    sm = registry.getSiteManager()
    for name, searcher in component.getUtilitiesFor(IContentSearcher):
        logger.info("Unregistering searcher %s = %r", name, searcher)
        sm.unregisterUtility(searcher,
                             provided=IContentSearcher,
                             name=name)
        searcher.__parent__ = None
        result += 1
    return result


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager config.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    root = conn.root()
    dataserver_folder = root['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = dataserver_folder
    component.provideUtility(mock_ds, IDataserver)

    with site(dataserver_folder):
        assert  component.getSiteManager() == dataserver_folder.getSiteManager(), \
                "Hooks not installed?"

        logger.info('Evolution %s started.', generation)

        result = _remover()
        for current_site in get_all_host_sites():
            with site(current_site):
                result += _remover(current_site)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s item(s) removed', generation, result)


def evolve(context):
    """
    Evolve generation 33 by removing registered contentsearcher objects
    """
    do_evolve(context)
