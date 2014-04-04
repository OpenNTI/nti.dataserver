#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, absolute_import, unicode_literals, division


#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import contains_string

import os.path

from nti.contentrendering.tests import simpleLatexDocumentText
from . import ContentrenderingLayerTest
from nti.contentrendering.tests import RenderContext

from nti.contentrendering import nti_render
from nti.contentrendering import transforms

from nti.contentrendering.resources.ResourceDB import ResourceDB

from zope.dublincore import xmlmetadata

class TestNTIRender(ContentrenderingLayerTest):

	def test_write_metadata(self):
		preludes = (br'\author{Jason}', br'\author{Steve}', br'\title{Staggering Work}')
		body = br"""
		 """
		text = simpleLatexDocumentText( bodies=(body, ), preludes=preludes )


		with RenderContext( text ) as ctx:
			nti_render.write_dc_metadata( ctx.dom, 'jobname' )

			fname = os.path.join( ctx.docdir, 'dc_metadata.xml' )

			metadata = xmlmetadata.parse( fname )

			assert_that( metadata, has_entry( 'Creator', ('Jason','Steve') ) )
			assert_that( metadata, has_entry( 'Title', ('Staggering Work',) ) )


	def test_dont_destroy_non_bmp_chars(self):
		# This is 'mathematical italic small tau', a character
		# that lives outside the BMP. It requires four utf-8 bytes
		# to encode, or two in utf-16 and cannot be encoded in ascii.
		# if we are on a "narrow" python build, it will require two
		# chars of storage, whereas a "wide" python build will use one char
		# (Python 3 will always use one char)
		tau = u"\U0001D70F"

		# right now, we expect to be on narrow builds
		assert_that( tau, has_length(2) )

		body = "\\includegraphics{Glossary.png} This is some text $z^2$ \\[t^3\\]" + tau


		text = simpleLatexDocumentText(bodies=(body,),
									   preludes=(br'\usepackage{graphicx}',))

		# Our default rendering process with default output encodings
		with RenderContext(text, input_encoding='utf-8',
						   files=(os.path.join(os.path.dirname(__file__), 'Glossary.png'),)) as ctx:
			transforms.performTransforms(ctx.dom)

			rdb = ResourceDB( ctx.dom )
			rdb.overrides['$z^2$'] = ('png',)
			rdb.overrides[r'\[t^3\]'] = ('svg',)

			rdb.generateResourceSets()

			nti_render.render(ctx.dom, 'XHTML', rdb)
			fname = os.path.join(ctx.docdir, 'tag_nextthought_com_2011-10_testing-HTML-temp_0.html')
			with open(fname, 'r') as f:
				contents = f.read()

			assert_that( contents,
						 contains_string('This is some text') )
			assert_that( contents, contains_string('&#120591'))

			# Now the post processing
			nti_render.postRender(ctx.dom)

			with open(fname, 'r') as f:
				contents = f.read()

			assert_that( contents,
						 contains_string('This is some text') )
			assert_that( contents, contains_string('&#120591'))
