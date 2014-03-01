#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904



from hamcrest import assert_that
from hamcrest import has_property

from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import ContentrenderingLayerTest
from nti.contentrendering.tests import RenderContext

from nti.contentrendering.resources import ResourceRenderer

class TestResourceRenderer(ContentrenderingLayerTest):

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
