# -*- coding: utf-8 -*-
"""
Content search generation 12.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 12

from ._utils import reindex_all
						
def evolve(context):
	"""
	Evolve generation 11 to generation 12 by reindexing in the user space
	"""
	reindex_all(context)
		
