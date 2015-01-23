#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Just like generation 36, now with better weakrefs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 40

from .evolve36 import evolve
evolve = evolve
