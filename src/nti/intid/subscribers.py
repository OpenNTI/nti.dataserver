#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component import handle

from zc.intid.interfaces import ISubscriberEvent


@component.adapter(ISubscriberEvent)
def subscriberEventNotify(event):
    """
    Event subscriber to dispatch ISubscriberEvent to interested adapters.
    """
    handle(event.object, event)
