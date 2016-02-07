#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for the Apple Push Notification Service.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.apns.connection import to_packet_bytes
