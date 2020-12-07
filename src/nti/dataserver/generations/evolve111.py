#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from .install import install_zope_authentication

logger = __import__('logging').getLogger(__name__)

generation = 111


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
