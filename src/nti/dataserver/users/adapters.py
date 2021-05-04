#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component
from zope import interface

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IPrincipal

from nti.dataserver.users import User

logger = __import__('logging').getLogger(__name__)


def _profile_to_user(profile):
    parent = getattr(profile, '__parent__')
    if IUser.providedBy(parent):
        return parent
    return None


@component.adapter(IPrincipal)
@interface.implementer(IUser)
def _principal_to_user(prin):
    return User.get_user(prin.id)
