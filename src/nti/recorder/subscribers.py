#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver_core.interfaces import IRecordableAnnotatable

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

@component.adapter(IRecordableAnnotatable, IObjectModifiedFromExternalEvent)
def _record_modification(obj, event):
    pass
