#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.authentication.interfaces import IAuthentication

logger = __import__('logging').getLogger(__name__)

generation = 111


def install_zope_authentication(dataserver_folder):
    from nti.app.authentication import _DSAuthentication

    lsm = dataserver_folder.getSiteManager()
    lsm.registerUtility(_DSAuthentication(), provided=IAuthentication)


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    install_zope_authentication(ds_folder)

    logger.info('Evolution %s done.', generation)


def evolve(context):
    """
    Evolve to generation 111 by adding a zope authorization utility
    to the DS folder
    """
    do_evolve(context, generation)
