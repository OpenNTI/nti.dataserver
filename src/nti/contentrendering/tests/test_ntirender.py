#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import has_entry

import os.path

from nti.contentrendering.tests import simpleLatexDocumentText, ConfiguringTestBase
from nti.contentrendering.tests import RenderContext

from nti.contentrendering import nti_render
from zope.dublincore import xmlmetadata

class TestNTIRender(ConfiguringTestBase):

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
