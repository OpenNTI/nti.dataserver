#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Payload support.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface

from . import interfaces as apns_interfaces

from nti.utils.schema import SchemaConfigured


@interface.implementer(apns_interfaces.INotificationPayload)
class APNSPayload(SchemaConfigured):
	""" Represents the payload of a APNs remote notification. """

	DEFAULT_SOUND = 'default'

	alert = None
	badge = None
	sound = None
	userInfo = None
