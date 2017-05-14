#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zc.intid.subscribers import addIntIdSubscriber
from zc.intid.subscribers import removeIntIdSubscriber


def addIntId(ob, event=None):
    addIntIdSubscriber(ob, event)
add_intid = addIntId


def removeIntId(ob, event=None):
    removeIntIdSubscriber(ob, event)
remove_intid = removeIntId
