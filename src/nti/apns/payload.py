#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Payload support.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.schema.fieldproperty import createFieldProperties

from nti.apns.interfaces import INotificationPayload

from nti.schema.schema import SchemaConfigured

@interface.implementer(INotificationPayload)
class APNSPayload(SchemaConfigured):
	"""
	Represents the payload of a APNs remote notification.
	"""

	DEFAULT_SOUND = 'default'

	createFieldProperties(INotificationPayload)
