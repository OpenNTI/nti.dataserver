# -*- coding: utf-8 -*-
"""
Content search generation 19.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 19

from ._utils import reindex_all
		
def evolve(context):
	"""
	Evolve generation 18 to 19 by reindexing all.
	"""
	reindex_all(context)