#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subscribers for various events.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component.event import objectEventNotify

from pyramid.interfaces import INewRequest


@component.adapter(INewRequest)
def requestEventNotify(event):
    """
    Just like :class:`zope.component.interfaces.IObjectEvent`,
    an :class:`.INewRequest` event wraps an object
    that may be of different types. This subscribers
    does double-dispatch.
    """
    event.object = event.request
    objectEventNotify(event)
