#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from six import string_types

from nti.dataserver.interfaces import system_user

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ISystemUserPrincipal

from nti.dataserver.users.users import User


def get_user(principal):
    if IUser.providedBy(principal):
        return principal
    elif ISystemUserPrincipal.providedBy(principal):
        return system_user
    if isinstance(principal, string_types):
        if principal == system_user.id:
            return system_user
        else:
            return User.get_user(principal)
    if principal is not None:
        return User.get_user(principal.id)
    return None
