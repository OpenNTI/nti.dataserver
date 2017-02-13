#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from six import string_types

from nti.dataserver.interfaces import ISystemUserPrincipal

from nti.dataserver.users.users import User


def get_user(principal):
    if ISystemUserPrincipal.providedBy(principal):
        return principal
    pid = principal if isinstance(principal, string_types) else principal.id
    return User.get_user(pid)
