#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.threadlocal import get_current_request

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.interfaces import IDisplayNameAdapter

logger = __import__('logging').getLogger(__name__)


class _Displayname(object):

    __slots__ = ('displayname',)

    def __init__(self, name):
        self.displayname = name


@component.adapter(IUser)
@interface.implementer(IDisplayNameAdapter)
def _user_to_displayname(context):
    generator = component.queryMultiAdapter((context, get_current_request()),
                                            IDisplayNameGenerator)
    name = generator() if generator is not None else None
    if name:
        return _Displayname(name)
