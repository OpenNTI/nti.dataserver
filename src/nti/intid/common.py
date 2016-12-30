#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zc.intid.subscribers import addIntIdSubscriber
from zc.intid.subscribers import removeIntIdSubscriber

def addIntId(ob, event=None):
	addIntIdSubscriber(ob, event)
intid_register = addIntId

def removeIntId(ob, event=None):
	removeIntIdSubscriber(ob, event)
intid_unregister = removeIntId
