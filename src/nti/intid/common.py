#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zc.intid.subscribers import addIntIdSubscriber
from zc.intid.subscribers import removeIntIdSubscriber

logger = __import__('logging').getLogger(__name__)


def addIntId(ob, event=None):
    addIntIdSubscriber(ob, event)
add_intid = addIntId


def removeIntId(ob, event=None):
    removeIntIdSubscriber(ob, event)
remove_intid = removeIntId
