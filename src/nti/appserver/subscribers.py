#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subscribers for various events.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import INewRequest

from zope import component

from zope.component.event import objectEventNotify

logger = __import__('logging').getLogger(__name__)


@component.adapter(INewRequest)
def requestEventNotify(event):
    """
    Just like :class:`zope.interface.interfaces.IObjectEvent`,
    an :class:`.INewRequest` event wraps an object
    that may be of different types. This subscribers
    does double-dispatch.
    """
    event.object = event.request
    objectEventNotify(event)
