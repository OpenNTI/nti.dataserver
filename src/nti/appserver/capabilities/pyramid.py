#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration between pyramid and capabilities.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Specifically, a custom predicate to check capabilities
