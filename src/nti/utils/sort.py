# -*- coding: utf-8 -*-
"""
Sort utilities

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from itertools import ifilter, tee

def isorted(iterable, comparator=None):
	"""
	generator-based quicksort.
	
	http://code.activestate.com/recipes/280501-lazy-sorting/
	"""
	try:
		iterable = iter(iterable)
		pivot = iterable.next()
	except (TypeError, StopIteration):
		return

	comparator = comparator if comparator else lambda x,y: x < y
		
	a, b = tee(iterable)
	for x in isorted(ifilter(lambda x: comparator(x, pivot), a), comparator):
		yield x
	yield pivot
	for x in isorted(ifilter(lambda x: not comparator(x, pivot), b), comparator):
		yield x
