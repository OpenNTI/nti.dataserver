#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.app.notabledata.interfaces import IUserNotableDataStorage

def store_circled_event_notable(change, event):
	owner = change.__parent__
	storage = IUserNotableDataStorage(owner)
	storage.store_object(change, safe=True, take_ownership=False)
