#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os
import shutil
from hamcrest import assert_that, is_, has_length, contains_string
from hamcrest import has_property

import tempfile
import StringIO

import plasTeX
from plasTeX.TeX import TeX


from nti.contentrendering.tests import simpleLatexDocumentText, ConfiguringTestBase
from nti.contentrendering.tests import RenderContext

from nti.contentrendering.resources import ResourceRenderer, Resource

class TestResourceRenderer(ConfiguringTestBase):

	def test_resourcerenderer(self):
		body = br"""
			\begin{tabular}{cc}
		   Noblewomen & Black \\
		   Middle-class & Red \\
		   Poor women & Blond \\
		 \end{tabular}"""
		text = simpleLatexDocumentText( bodies=(body, ) )

		class MockResourceDB(object):
			def getResource(self, *args):
				return MockImage()

		class MockImage(object):
			path = None
			url = None
			height = width = { 'px': 1 }

		with RenderContext( text ) as ctx:

			#res_db = nti_render.generateImages( ctx.dom )
			renderer = ResourceRenderer.createResourceRenderer( 'XHTML', MockResourceDB() )

			renderer.render( ctx.dom )

			# Its renderers should now claim to be enabled
			assert_that( renderer, has_property( 'vectorImager', has_property( 'enabled', True ) ) )
			assert_that( renderer, has_property( 'imager', has_property( 'enabled', True ) ) )
