# -*- coding: utf-8 -*-
"""
Content search generation 24.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 24

from .evolve23 import do_evolve

def evolve(context):
	"""
	Evolve generation 23 to 24 by reindexing redactions.
	"""
	do_evolve(context)
