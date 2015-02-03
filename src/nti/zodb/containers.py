#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to nti.common",
	"nti.common.time",
	"time_to_64bit_int",
	"bit64_int_to_time",
	"ZERO_64BIT_INT",
	"_long_to_double_bits",
	"_double_bits_to_long",
	"_long_to_double_bits",
	"_float_to_double_bits")