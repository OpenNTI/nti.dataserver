#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Various python3/pypy compatibility shims.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

try:
	from gevent import sleep
except ImportError:
	from time import sleep

sleep = sleep  # pylint