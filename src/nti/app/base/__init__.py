#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic components for the application. This consists of non-domain-specific components.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.cabinet.interfaces import ISource
from nti.cabinet.interfaces import IMultipartSource
