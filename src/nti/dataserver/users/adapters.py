#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.dataserver.interfaces import IUser

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def _profile_to_user(profile):
    parent = getattr(profile, '__parent__')
    if IUser.providedBy(parent):
        return parent
    return None
