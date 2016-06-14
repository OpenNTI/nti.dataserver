#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.coremetadata.interfaces import IPublishable
from nti.coremetadata.interfaces import IObjectPublishedEvent
from nti.coremetadata.interfaces import IObjectUnpublishedEvent

from nti.recorder.utils import record_transaction

_TRX_TYPE_PUBLISH = 'publish'
_TRX_TYPE_UNPUBLISH = 'unpublish'

@component.adapter(IPublishable, IObjectPublishedEvent)
def _record_published(obj, event):
	record_transaction(obj, type_=_TRX_TYPE_PUBLISH)

@component.adapter(IPublishable, IObjectUnpublishedEvent)
def _record_unpublished(obj, event):
	record_transaction(obj, type_=_TRX_TYPE_UNPUBLISH)
