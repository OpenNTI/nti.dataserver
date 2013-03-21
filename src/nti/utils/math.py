# -*- coding: utf-8 -*-
"""
Math utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import math

class AffineMatrix(object):

	def __init__(self, a=None, b=None, c=None, d=None, tx=None, ty=None):
		a = 1.0 if a is None else a
		b = 0.0 if b is None else b
		c = 0.0 if c is None else c
		d = 1.0 if d is None else d
		tx = 0.0 if tx is None else tx
		ty = 0.0 if ty is None else ty
		self.m = [a, b, c, d, tx, ty]

	@property
	def tx(self):
		return self.m[4]

	@property
	def ty(self):
		return self.m[5]

	def reset(self):
		self.m = [1.0, 0.0, 0.0 , 1.0, 0.0, 0.0]

	def multiply(self, matrix):
		m11 = self.m[0] * matrix.m[0] + self.m[2] * matrix.m[1]
		m12 = self.m[1] * matrix.m[0] + self.m[3] * matrix.m[1]

		m21 = self.m[0] * matrix.m[2] + self.m[2] * matrix.m[3]
		m22 = self.m[1] * matrix.m[2] + self.m[3] * matrix.m[3]

		dx = self.m[0] * matrix.m[4] + self.m[2] * matrix.m[5] + self.m[4]
		dy = self.m[1] * matrix.m[4] + self.m[3] * matrix.m[5] + self.m[5]

		self.m[0] = m11
		self.m[1] = m12
		self.m[2] = m21
		self.m[3] = m22
		self.m[4] = dx
		self.m[5] = dy

	def rotate(self, rad):
		c = math.cos(rad)
		s = math.sin(rad)
		self.multiply(*[c, s, -s, c, 0.0, 0.0])

	def translate(self, x, y=None):
		if isinstance(x, (list, tuple)):
			y = x[1]
			x = x[0]

		self.multiply(*[1.0 , 0.0, 0.0, 1.0, x, y])

	def scale(self, sx, sy=None):
		if isinstance(sx, (list, tuple)):
			sx = sx[0]
			sy = sx[1]

		sy = sx is sy if None else sy
		self.multiply(*[sx, 0.0, 0.0, sy, 0.0, 0.0])

	def scale_all(self, scale):
		i = len(self.m) - 1
		while (i >= 0):
			self.m[i] *= scale
			i = i - 1
	scaleAll = scale_all

	def get_scale(self, averaged=False):
		m = self.m
		a = m[0]
		b = m[1]
		c = m[2]
		d = m[3]
		sx = math.sqrt(a * a + b * b)  # *(a<0? -1 : 1)
		sy = math.sqrt(c * c + d * d)  # *(d<0? -1 : 1)
		return (sx + sy) / 2.0 if averaged else [sx, sy]

	getScale = get_scale

	def get_rotation(self):
		m = self.m
		a = m[0]
		b = m[1]
		return math.atan2(b, a)

	getRotation = get_rotation

	def get_translation(self):
		return [self.m[4], self.m[5]]

	getTranslation = get_translation

	def transform_point(self, px, py=None):
		if isinstance(px, (list, tuple)):
			px = px[0]
			py = px[1]

		return [
			px * self.m[0] + py * self.m[2] + self.m[4],  # x
			px * self.m[1] + py * self.m[3] + self.m[5]  # y
		]

	transformPoint = transform_point

NTMatrix = AffineMatrix

def choose(n, k, *args):
	"""
	A fast way to calculate binomial coefficients by Andrew Dalke (contrib).
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

def comb(N, k, *args):
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
