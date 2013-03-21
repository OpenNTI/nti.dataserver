# -*- coding: utf-8 -*-
"""
Math utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import numpy as np

def choose(n, k, *args):
	"""
	A fast way to calculate binomial coefficients.
	"""
	if 0 <= k <= n:
		ntok = 1
		ktok = 1
		for t in xrange(1, min(k, n - k) + 1):
			ntok *= n
			ktok *= t
			n -= 1
		return ntok // ktok
	else:
		return 0

def combinations(N, k, *args):
	"""
	The number of combinations of N things taken k at a time
	"""
	if (k > N) or (N < 0) or (k < 0):
		return 0L
	N, k = map(long, (N, k))
	top = N
	val = 1L
	while (top > (N - k)):
		val *= top
		top -= 1
	n = 1L
	while (n < k + 1L):
		val /= n
		n += 1
	return val

try:
	from scipy.misc import comb
except ImportError:
	comb = choose

def bernstein_poly(i, n, t):
	"""
	 The Bernstein polynomial of n, i as a function of t
	"""
	return comb(n, i) * (t ** (n - i)) * (1 - t) ** i

def bezier_curve(x_points, y_points, nTimes=1000):
	"""
   Given a set of control points, return the
   bezier curve defined by the control points.

   points should be a list of lists, or list of tuples
   such as [ [1,1], 
			 [2,3], 
			 [4,5], ..[Xn, Yn] ]
	nTimes is the number of time steps, defaults to 1000

	See http://processingjs.nihongoresources.com/bezierinfo/
	"""

	nPoints = len(x_points)
	xPoints = np.array(x_points)
	yPoints = np.array(y_points)

	t = np.linspace(0.0, 1.0, nTimes)

	polynomial_array = np.array([ bernstein_poly(i, nPoints - 1, t) for i in range(0, nPoints)   ])

	xvals = np.dot(xPoints, polynomial_array)
	yvals = np.dot(yPoints, polynomial_array)

	return xvals, yvals
