# -*- coding: utf-8 -*-
"""
Graphics utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import math

rgb_pattern = re.compile(u'rgb\((?P<r>(\d+)(\.\d+)?),(?P<g>(\d+)(\.\d+)?),(?P<b>(\d+)(\.\d+)?)\)', re.UNICODE)

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

def check_width(width):
	if width is not None:
		width = 1 if math.isinf(width) or math.isnan(width) else width
	return width

def check_rgb_color(fill, default="rgb(0,0,0)"):
	if fill:
		fill_mod = re.sub('\s', '', fill).lower()
		m = rgb_pattern.search(fill_mod)
		if m is not None:
			d = m.groupdict()
			fill = "rgb(%s,%s,%s)" % (int(float(d['r'])), int(float(d['g'])), int(float(d['b'])))
	return fill or default

def plot_bezier_curve(draw, xvals, yvals, fill=None, width=None, m=None):
	"""
	plot the curve specified x,y coordinates
	
	:param draw: Pillow Image.Draw object
	:param xvals: X-coordinates
	:param yvals: Y-coordinates
	:param m: Affine matrix
	:param fill: The color to use for the curve
	:width width curve width
	"""
	length = min(len(xvals), len(yvals))
	fill = check_rgb_color(fill)
	width = check_width(width)
	for i in xrange(length):
		x = xvals[i]
		y = yvals[i]
		if m is not None:
			tx, ty = m.transform_point(x, y)
		else:
			tx, ty = x, y

		if not width:
			draw.point((tx, ty), fill=fill)
		else:
			# use ceil to make sure the line is properly drawn
			draw.line((tx, ty, math.ceil(tx), math.ceil(ty)), fill=fill, width=width)

plot_curve = plot_bezier_curve
