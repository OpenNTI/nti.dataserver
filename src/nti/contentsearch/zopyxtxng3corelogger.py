# -*- coding: utf-8 -*-
"""
Zopyx override for logger.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

def Logger():
	return logger

PyLogger = Logger

Z2Logger = Logger

LOG = logger
