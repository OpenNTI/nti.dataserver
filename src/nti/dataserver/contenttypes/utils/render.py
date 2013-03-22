# -*- coding: utf-8 -*-
"""
Canvas / Pillow rendering methods

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.utils import graphics
# from nti.utils import math as nti_math

def square(draw, polygon,):
	"""
	render a Cavas.CanvasPolygonShape with 4 sides
	
	adapted from NextThought/view/whiteboard/shapes/Polygon.js
	"""
	assert polygon.sides == 4

	transform = polygon.transform.toArray()
	width, _ = draw.im.size
	m = graphics.AffineMatrix(*transform)
	m.scaleAll(width)
	# scale = m.getScale(True)

	x = -0.5
	y = -0.5
	w = 1
	h = 1

	tpx, tpy = m.transformPoint(x, y)
	tx, ty = m.transformPoint(x + w, y)
	draw.line((tpx, tpy, tx, ty))

	tpx, tpy = tx, ty
	tx, ty = m.transformPoint(x + w, y + h)
	draw.line((tpx, tpy, tx, ty))

	tpx, tpy = tx, ty
	tx, ty = m.transformPoint(x, y + h)
	draw.line((tpx, tpy, tx, ty))

	tpx, tpy = tx, ty
	tx, ty = m.transformPoint(x, y)
	draw.line((tpx, tpy, tx, ty))

