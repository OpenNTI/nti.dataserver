#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.appserver.interfaces import IUserContainersQuerier

from nti.dataserver.interfaces import IUser

from nti.ntiids.ntiids import ROOT

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IUserContainersQuerier)
class _UserContainersQuerier(object):

    def __init__(self, user=None):
        self.user = user

    def query(self, user, ntiid, include_stream, stream_only):
        containers = set()
        user = self.user if user is None else user
        if ntiid == ROOT:
            containers.update(user.iterntiids(include_stream=include_stream,
                                              stream_only=stream_only))
        # We always include the unnamed root (which holds things like CIRCLED)
        # NOTE: This is only in the stream. Normally we cannot store contained
        # objects with an empty container key, so this takes internal magic
        containers.add('')  # root
        return containers
    __call__ = query
