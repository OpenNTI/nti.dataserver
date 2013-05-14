#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals
import os
from hamcrest import assert_that, is_, has_length, contains_string
from hamcrest import has_property
from hamcrest import contains, has_item
from hamcrest import has_entry
from hamcrest import is_not as does_not
import unittest

import plasTeX
from plasTeX.TeX import TeX

from ..ntiassessment import naquestion, naquestionset

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import RenderContext

import nti.tests

import nti.contentrendering
import nti.assessment
import nti.externalization

def _simpleLatexDocument(maths):
	return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}',
											  br'\usepackage{graphicx}'),
									bodies=maths )

# Nose module-level setup and teardown
setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentrendering,nti.assessment,nti.externalization) )
tearDownModule = nti.tests.module_teardown


from nti.contentrendering.plastexpackages import interfaces
from zope import component
from zope import interface
from nti.contentrendering import interfaces as cdr_interfaces
from nti.contentrendering.resources import ResourceRenderer
import io

@interface.implementer(cdr_interfaces.IRenderedBook)
class _MockRenderedBook(object):
	document = None
	contentLocation = None


class TestNTICard(unittest.TestCase):

	def _do_test_render( self, label, ntiid, filename='index.html', input_encoding=None, caption=r'\caption{Unknown}', caption_html=None,
						 href='[/foo/bar]',
						 options='[creator=biz baz]',
						 image=r'\includegraphics[width=100px]{test.png}',
						 content='',
						 do_images=True):

		example = br"""
		\begin{nticard}%(href)s%(options)s
		%(label)s
		%(caption)s
		%(image)s
		%(content)s
		\end{nticard}
		""" % {'label': label, 'caption': caption, 'href': href, 'options': options, 'image': image, 'content': content }
		__traceback_info__ = example
		with RenderContext(_simpleLatexDocument( (example,) ), output_encoding='utf-8', input_encoding=input_encoding,
						   files=(os.path.join( os.path.dirname(__file__ ), 'test.png' ),),
						   packages_on_texinputs=True) as ctx:

			dom  = ctx.dom
			dom.getElementsByTagName( 'document' )[0].filenameoverride = 'index'
			res_db = None
			if do_images:
				from nti.contentrendering import nti_render
				res_db = nti_render.generateImages( dom )

			render = ResourceRenderer.createResourceRenderer('XHTML', res_db)
			render.importDirectory( os.path.join( os.path.dirname(__file__), '..' ) )
			render.render( dom )
			# TODO: Actual validation of the rendering


			with io.open(os.path.join(ctx.docdir, filename), 'rU', encoding='utf-8' ) as f:
				index = f.read()
			content = """<object type="application/vnd.nextthought.nticard" class="nticard" data-ntiid="%(ntiid)s" """ % { 'ntiid': ntiid }
			content2 = """<param name="ntiid" value="%(ntiid)s" """ % { 'ntiid': ntiid }

			assert_that( index, contains_string( content ) )
			assert_that( index, contains_string( content2 ) )

			if caption and caption_html:
				assert_that( index, contains_string( 'data-title="%s"' % caption_html ) )
				assert_that( index, contains_string( '<param name="title" value="%s"' % caption_html ) )

			return index

	def test_render_id(self):
		"The label for the question becomes part of its NTIID."
		self._do_test_render( r'\label{testcard}', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.testcard')

	def test_render_counter(self):
		self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1' )

	def test_computed_target_ntiid(self):
		index = self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1' )
		assert_that( index, contains_string( 'data-target_ntiid="tag:nextthought.com,2011-10:NTI-UUID-1df481b1ec67d4d8bec721f521d4937d"' ) )

	def test_actual_target_ntiid(self):
		from nti.ntiids.ntiids import make_ntiid
		target_ntiid = make_ntiid( provider='OU', nttype='HTML', specific='abc' )
		index = self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1',
									  href='[%s]' % target_ntiid )
		assert_that( index, contains_string( 'data-target_ntiid="%s"' % target_ntiid ) )
		assert_that( index, contains_string( 'data-creator="biz baz"') )

	def test_render_caption_as_title(self):
		self._do_test_render( r'\label{testcard}', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.testcard',
							  caption=r'\caption{The Title}', caption_html='The Title')

	def test_render_description(self):
		value = self._do_test_render( r'\label{testcard}', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.testcard',
									  content='This is the description.',
									  do_images=True)
		assert_that( value, contains_string( '<span class="description">This is the description.</span>' ) )
		assert_that( value, contains_string( '<img ' ) )
