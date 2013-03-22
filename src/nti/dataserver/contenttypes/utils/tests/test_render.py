#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from PIL import Image, ImageDraw

from .. import render
from ... import canvas

from nti.externalization.internalization import update_from_external_object

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, none)

class TestRender(ConfiguringTestBase):

	def test_parse_number(self):
		assert_that(render.parse_number('0.012%'), is_(0.012))
		assert_that(render.parse_number('2'), is_(2))
		assert_that(render.parse_number('xrtd'), is_(none()))

	def test_draw_rectangle(self):

		data = {"Class": "CanvasPolygonShape",
				"MimeType": "application/vnd.nextthought.canvaspolygonshape",
				"fillColor": "rgb(43.0,137.0,197.0)",
				"fillOpacity": 1.0,
				"fillRGBAColor": "0.169 0.537 0.772",
				"sides": 4,
				"strokeColor": "rgb(211.0,79.0,57.0)",
				"strokeOpacity": 1.0,
				"strokeRGBAColor": "0.828 0.310 0.224",
				"strokeWidth": "0.012%",
				"transform": {"Class": "CanvasAffineTransform", "MimeType": "application/vnd.nextthought.canvasaffinetransform",
							  "a": 0.23796791443850265, "b": 0, "c": 0, "d": 0.23796791443850265, "tx": 0.391711229946524, "ty": 0.23529411764705882 }
				}

		polygon = canvas.CanvasPolygonShape()
		update_from_external_object(polygon, data)

		image = Image.new("RGBA", (600, 600), (0, 0, 0))
		draw = ImageDraw.Draw(image)
		render.draw_rectangle(draw, polygon)
		# image.show()
