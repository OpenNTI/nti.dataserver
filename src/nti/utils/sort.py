# -*- coding: utf-8 -*-
"""
Sort utilities

$Id: _search_utils.py 16109 2013-02-20 22:29:23Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from itertools import ifilter, tee

def isorted(iterable, comparator=None):
	"""
	generator-based quicksort.
	
	http://code.activestate.com/recipes/280501-lazy-sorting/
	"""
	iterable = iter(iterable)
	try:
		pivot = iterable.next()
	except:
		return

	comparator = comparator if comparator else lambda x,y: x < y
		
	a, b = tee(iterable)
	for x in isorted(ifilter(lambda x: comparator(x, pivot), a), comparator):
		yield x
	yield pivot
	for x in isorted(ifilter(lambda x: not comparator(x, pivot), b), comparator):
		yield x
