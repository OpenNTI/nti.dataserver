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

from zope.authentication.interfaces import IAuthentication

from zope.component.hooks import site as current_site

from nti.app.authentication import _DSAuthentication

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.interfaces import IOIDResolver

from nti.site import get_all_host_sites

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

        for site in get_all_host_sites():
            logger.info("Rebuilding site manager for %s", site.__name__)
            sm = site.getSiteManager()
            sm.rebuild()
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 113 by rebuilding registry sub types.
    """
    do_evolve(context, generation)
