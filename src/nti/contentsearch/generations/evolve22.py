# -*- coding: utf-8 -*-
"""
Content search generation 22.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 22

from .evolve20 import do_evolve

def evolve(context):
	"""
	Evolve generation 21 to 22 by reindexing posts.
	"""
	do_evolve(context)
