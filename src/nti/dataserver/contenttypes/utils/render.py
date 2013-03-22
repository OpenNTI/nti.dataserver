# -*- coding: utf-8 -*-
"""
Canvas / Pillow rendering methods

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import math
from nti.utils import graphics
# from nti.utils import math as nti_math

def parse_number(n):
	n = re.sub("[^\d\.]", '', n)
	try:
		return float(n) if n else None
	except:
		return None

def _ic(v):
	return int(math.ceil(v))

def _get_line_width(shape, width, scale):
	factor = -1.0 if scale < 0 else 1.0
	sw = shape.strokeWidth
	stroke_width = parse_number(sw)
	stroke_width = stroke_width * 100 if sw.endswith('%') else stroke_width
	if stroke_width:
		line_width = (stroke_width * width) / scale * factor
		line_witdh = int (math.ceil(line_width))
	else:
		line_width = 1
	return line_witdh

def draw_rectangle(draw, polygon):
	"""
	render a Cavas.CanvasPolygonShape with 4 sides
	
	adapted from NextThought/view/whiteboard/shapes/Polygon.js
	"""
	assert polygon.sides == 4

	transform = polygon.transform.toArray()
	width, _ = draw.im.size
	m = graphics.AffineMatrix(*transform)
	m.scale_all(width)
	scale = m.get_scale(True)
	line_width = _get_line_width(polygon, width, scale)
	fill_color = graphics.check_rgb_color(polygon.fillColor)
	stroke_color = graphics.check_rgb_color(polygon.strokeColor)

	x, y = -0.5, -0.5
	w, h = 1, 1

	tpx, tpy = m.transform_point(x, y)
	tx, ty = m.transform_point(x + w, y + h)
	box = (_ic(tpx), _ic(tpy), _ic(tx), _ic(ty))

	draw.rectangle(box, fill=stroke_color)  # The outer rectangle6
	draw.rectangle(# The inner rectangle
		(box[0] + line_width, box[1] + line_width, box[2] - line_width, box[3] - line_width),
		fill=fill_color)

# 	tpx, tpy = m.transform_point(x, y)
# 	tx, ty = m.transform_point(x + w, y)
# 	draw.line((tpx, tpy, tx, ty), width=line_width, fill=fill_color)
#
# 	tpx, tpy = tx, ty
# 	tx, ty = m.transform_point(x + w, y + h)
# 	draw.line((tpx, tpy, tx, ty), width=line_width, fill=fill_color)
#
# 	tpx, tpy = tx, ty
# 	tx, ty = m.transform_point(x, y + h)
# 	draw.line((tpx, tpy, tx, ty), width=line_width, fill=fill_color)
#
# 	tpx, tpy = tx, ty
# 	tx, ty = m.transform_point(x, y)
# 	draw.line((tpx, tpy, tx, ty), width=line_width, fill=fill_color)
