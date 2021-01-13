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

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.interfaces import IOIDResolver

from nti.site import get_all_host_sites

logger = __import__('logging').getLogger(__name__)

generation = 112


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


def remove_authentication_util(site):
    sm = site.getSiteManager()

    registered_auths = [reg for reg in sm.registeredUtilities()
                        if (reg.provided.isOrExtends(IAuthentication))
                        and reg.name == '']

    if registered_auths:
        sm.unregisterUtility(registered_auths[0].component,
                             IAuthentication)

    auth = sm.get('default', {}).get('authentication')
    if auth is not None:
        del sm['default']['authentication']


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        remove_authentication_util(ds_folder)

        from nti.app.authentication.subscribers import install_site_authentication
        for site in get_all_host_sites():
            install_site_authentication(site.getSiteManager())
    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 112 by adding a zope authentication utility
    to all host sites and removing the previous utility registered on
    the dataserver folder
    """
    do_evolve(context, generation)
