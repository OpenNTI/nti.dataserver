#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zc.intid.interfaces import IAfterIdAddedEvent as INTIIntIdAddedEvent
from zc.intid.interfaces import IBeforeIdRemovedEvent as INTIIntIdRemovedEvent

from zc.intid.interfaces import AfterIdAddedEvent as NTIIntIdAddedEvent
from zc.intid.interfaces import BeforeIdRemovedEvent as NTIIntIdRemovedEvent
