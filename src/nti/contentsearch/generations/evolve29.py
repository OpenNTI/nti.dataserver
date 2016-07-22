#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content search generation 29.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 29

from nti.contentsearch.generations.evolve28 import do_evolve

def evolve(context):
	"""
	Evolve generation 28 to 29 by removing all legach search index data
	"""
	do_evolve(context)
