#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import uuid

from zope import interface

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IUsernameGeneratorUtility


@interface.implementer(IUsernameGeneratorUtility)
class OpaqueUsernameGeneratorUtility(object):
    """
    Generate a unique, opaque username.
    """

    def _make_username(self):
        return str(uuid.uuid4().get_time_low())

    def generate_username(self):
        username = self._make_username()
        while User.get_user(username) is not None:
            username = self._make_username()
        return username
