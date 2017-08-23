#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions and architecture for general activity streams.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver.interfaces import INotableFilter
from nti.dataserver.interfaces import IStreamChangeCircledEvent


@interface.implementer(INotableFilter)
class CircledNotableFilter(object):
    """
    Check to see if the given object is a circled event for our user.
    """

    # We currently only store circled events in the user's storage.
    # Therefore, let's check for that specific object when determining
    # notability.  We could also check the user's storage (safe and unsafe)
    # like the legacy algorithm does.

    def __init__(self, context):
        self.context = context

    def is_notable(self, obj, user):
        return  IStreamChangeCircledEvent.providedBy(obj) \
            and obj.__parent__ == user


@interface.implementer(INotableFilter)
class ReplyToNotableFilter(object):
    """
    Determines if an object is notable by checking to see if it is a
    reply to something we created.
    """

    def __init__(self, context):
        self.context = context

    def is_notable(self, obj, user):
        result = False
        obj_creator = getattr(obj, 'creator', None)
        obj_parent = getattr(obj, 'inReplyTo', None)
        parent_creator = getattr(obj_parent, 'creator', None)
        if      obj_creator is not None \
            and obj_parent is not None \
            and obj_creator != user \
            and parent_creator == user:
            result = True
        return result
