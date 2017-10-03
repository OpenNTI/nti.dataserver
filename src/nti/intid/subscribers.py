#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.component import handle

from zc.intid.interfaces import ISubscriberEvent

logger = __import__('logging').getLogger(__name__)


@component.adapter(ISubscriberEvent)
def subscriberEventNotify(event):
    """
    Event subscriber to dispatch ISubscriberEvent to interested adapters.
    """
    handle(event.object, event)
