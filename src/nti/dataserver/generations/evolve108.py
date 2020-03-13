#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.dataserver.authorization import ROLE_ADMIN

logger = __import__('logging').getLogger(__name__)

generation = 108


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    ds_role_manager = IPrincipalRoleManager(ds_folder)

    users_processed = 0
    for user in ds_folder['users'].values() or ():
        if user.username.endswith("@nextthought.com"):
            logger.info('Processing %s', user.username)
            ds_role_manager.assignRoleToPrincipal(ROLE_ADMIN.id, user.username)
            users_processed += 1

    logger.info('Evolution %s done. Migrated %s nti admins.', generation, users_processed)


def evolve(context):
    """
    Evolve to generation 108 by adding nextthought.com users as nti admins.
    """
    do_evolve(context, generation)

