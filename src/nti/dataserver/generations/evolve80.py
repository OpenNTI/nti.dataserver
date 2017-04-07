#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 80

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from nti.invitations.index import install_invitations_catalog
from nti.invitations.model import install_invitations_container


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

        install_invitations_catalog(ds_folder, intids)
        install_invitations_container(ds_folder, intids)
        logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 80 by installing the new invitations catalog and container
    """
    do_evolve(context)
