# -*- coding: utf-8 -*-
"""
Content search generation 19.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 21

from . import evolve20
		
def evolve(context):
	"""
	Evolve generation 20 to 21 by reindexing posts.
	"""
	evolve20.evolve(context)