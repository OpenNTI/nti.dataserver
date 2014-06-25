#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals, absolute_import

import os
from hamcrest import assert_that, contains_string, has_length, is_, has_property

import unittest

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import RenderContext

import fudge


def _simpleLatexDocument(maths):
	return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}',
											  br'\usepackage{graphicx}'),
									bodies=maths )


from zope import interface
from nti.contentrendering import interfaces as cdr_interfaces
from nti.contentrendering.resources import ResourceRenderer
import io

@interface.implementer(cdr_interfaces.IRenderedBook)
class _MockRenderedBook(object):
	document = None
	contentLocation = None

from . import ExtractorTestLayer

class TestNTICard(unittest.TestCase):
	layer = ExtractorTestLayer
	toc = None

	def setUp(self):
		super(TestNTICard,self).setUp()
		self.toc = None

	def _do_test_render( self, label, ntiid, filename='index.html', input_encoding=None,
						 prelude='',
						 caption=r'\caption{Unknown}', caption_html=None,
						 href='{/foo/bar}',
						 options='<creator=biz baz>',
						 image=r'\includegraphics[width=100px]{test.png}',
						 content='',
						 do_images=True):

		example = br"""
		%(prelude)s
		\begin{nticard}%(href)s%(options)s
		%(label)s
		%(caption)s
		%(image)s
		%(content)s
		\end{nticard}
		""" % {'prelude': prelude, 'label': label, 'caption': caption, 'href': href, 'options': options, 'image': image, 'content': content }
		__traceback_info__ = example
		with RenderContext(_simpleLatexDocument( (example,) ), output_encoding='utf-8', input_encoding=input_encoding,
						   files=(os.path.join( os.path.dirname(__file__ ), 'test.png' ),
								  os.path.join( os.path.dirname(__file__ ), 'test_page574_12.pdf' ),),
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
			with io.open(os.path.join(ctx.docdir, 'eclipse-toc.xml'), 'rU', encoding='utf-8' ) as f:
				toc = f.read()
			self.toc = toc
			#print(toc)


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

	def test_container_in_toc(self):
		prelude = r'\section{A section}'
		self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1', prelude=prelude,
							  filename='tag_nextthought_com_2011-10_testing-HTML-temp_a_section.html')

		assert_that( self.toc,
					 contains_string( '''    <topic level="part" levelnum="1" label="A section" href="tag_nextthought_com_2011-10_testing-HTML-temp_a_section.html" ntiid="tag:nextthought.com,2011-10:testing-HTML-temp.a_section">
<object ntiid="tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1" mimeType="application/vnd.nextthought.nticard">
</object>''') )

		prelude = r'''\section{A section}
		Followed by some text

		and more text.

		\subsection{a subsection}'''
		self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1', prelude=prelude,
							  filename='tag_nextthought_com_2011-10_testing-HTML-temp_a_section.html')
		assert_that( self.toc,
					 contains_string( '''       <topic level="chapter" levelnum="2" label="a subsection" href="tag_nextthought_com_2011-10_testing-HTML-temp_a_section.html#a0000000002" ntiid="tag:nextthought.com,2011-10:testing-HTML-temp.a_subsection">
<object ntiid="tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1" mimeType="application/vnd.nextthought.nticard">''') )

	def test_computed_target_ntiid(self):
		index = self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1' )
		assert_that( index, contains_string( 'data-target_ntiid="tag:nextthought.com,2011-10:NTI-UUID-1df481b1ec67d4d8bec721f521d4937d"' ) )

	def test_actual_target_ntiid(self):
		from nti.ntiids.ntiids import make_ntiid
		target_ntiid = make_ntiid( provider='OU', nttype='HTML', specific='abc' )
		index = self._do_test_render( '', 'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1',
									  href='{%s}' % target_ntiid )
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

	@fudge.patch('requests.get')
	def test_auto_populate_remote_html(self, fake_get):
		# This real URL has been download locally
		html_file = os.path.join( os.path.dirname( __file__ ), '130107fa_fact_green.html' )
		jpeg_file = os.path.join( os.path.dirname( __file__ ), '130107_r23011_g120_cropth.jpg' )

		class R1(object):
			def __init__(self):
				self.headers = {'content-type': 'text/html'}
			@property
			def text(self):
				return open(html_file, 'r').read()

		class R2(object):
			@property
			def content(self):
				return open(jpeg_file, 'rb').read()

		fake_get.is_callable().returns( R1() ).next_call().returns( R2() )
		url = '{http://www.newyorker.com/reporting/2013/01/07/130107fa_fact_green?currentPage=all}'
		index = self._do_test_render(
			r'\label{testcard}',
			'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.testcard',
			caption='', caption_html='',
			options='<auto=True>',
			href=url,
			image='' )

		assert_that(index, contains_string('<span class="description">Apollo Robbins takes things from people’s jackets, pants, purses, wrists, fingers, and necks, then returns them in amusing and mind-boggling ways.</span>'))
		assert_that( index, contains_string( '<img src="http://www.newyorker.com/images/2013/01/07/g120/130107_r23011_g120_cropth.jpg" height="120" width="120"' ) )


	def test_auto_populate_local_pdf(self):
		index = self._do_test_render(
			r'\label{testcard}',
			'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.testcard',
			caption='', caption_html='',
			options='<auto=True>',
			href='{test_page574_12.pdf}', # local, relative path
			image='' )

		# Values from the PDF
		assert_that( index, contains_string( 'data-creator="Jason Madden"' ) )
		assert_that( index, contains_string( '<span class="description">Subject</span>' ) )

		# And we got a generated thumbnail
		assert_that( index, contains_string( '<img src="resources') )

	@fudge.patch('requests.get')
	def test_auto_populate_remote_pdf(self, fake_get=None):
		# By commenting out the patch line, we can test with a real file
		if fake_get is not None:
			# This real URL has been download locally
			pdf_file = os.path.join( os.path.dirname( __file__ ), 'test_page574_12.pdf' )

			class R1(object):
				def __init__(self):
					self.headers = {'content-type': 'application/pdf'}
					self.raw = open(pdf_file, 'rb')

			fake_get.is_callable().returns( R1() )
			href = '{http://someserver.com/path/to/test_page574_12.pdf}' # remote href
		else:
			href = '{http://support.pokemon.com/FileManagement/Download/f6029520f8ea43f08790ec4975944bb3}'
		index = self._do_test_render(
			r'\label{testcard}',
			'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.testcard',
			caption='', caption_html='',
			options='<auto=True>',
			href=href,
			image='' )

		# Values from the PDF
		assert_that( index, contains_string( 'data-creator="Jason Madden"' ) )
		assert_that( index, contains_string( '<span class="description">Subject</span>' ) )

		# And we got a generated thumbnail
		assert_that( index, contains_string( '<img src="resources') )

		# and the href
		assert_that( index, contains_string( 'data-href="http://someserver.com/path/to/test_' ) )

class TestRelatedWorkRef(unittest.TestCase):
	base_example = br"""
	\begin{relatedwork}
	\label{relwk:Selection_Sort} 
	\worktitle{Selection Sort}
	\workcreator{Wikipedia}
	\worksource{http://en.wikipedia.org/wiki/Selection_sort}
	\includegraphics{test}
	Explanation and visualizations of the selection sort algorithm.
	\end{relatedwork}

	\relatedworkref{relwk:Selection_Sort}{}{}
	"""

	def test_relatedworkref_basic(self):
		dom = _buildDomFromString( _simpleLatexDocument( (self.base_example,) ) )

		# Check that the DOM has the expected structure
		assert_that( dom.getElementsByTagName('relatedwork'), has_length( 1 ) )
		assert_that( dom.getElementsByTagName('relatedworkref'), has_length( 1 ) )

		relatedworkref_el = dom.getElementsByTagName('relatedworkref')[0]

		# Check that the relatedworkref object has the expected attributes
		assert_that( relatedworkref_el.category, contains_string( 'required' ) )
		assert_that( relatedworkref_el.description.source, contains_string( 'Explanation and visualizations of the selection sort algorithm.' ) )
		assert_that( relatedworkref_el.target_ntiid, contains_string( 'UUID' ) )
		assert_that( relatedworkref_el.targetMimeType, contains_string( 'application/vnd.nextthought.externallink' ) )
		assert_that( relatedworkref_el.uri, contains_string( 'http://en.wikipedia.org/wiki/Selection_sort' ) )
		assert_that( relatedworkref_el.visibility, contains_string( 'everyone' ) )
		
class TestSidebars(unittest.TestCase):

	def test_sidebar_basic(self):
		example = br"""
		\begin{sidebar}{Title}
		\label{sidebar:Basic_Sidebar}
		Body Text
		\end{sidebar}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

		# Check that the DOM has the expected structure
		assert_that( dom.getElementsByTagName('sidebar'), has_length( 1 ) )

		sidebar_el = dom.getElementsByTagName('sidebar')[0]

		# Check that the relatedworkref object has the expected attributes
		assert_that( sidebar_el.attributes.get('title').source, contains_string( 'Title' ) )
		assert_that( sidebar_el.childNodes[2].source, contains_string( 'Body Text' ) )

	def test_sidebar_basic_ntiid(self):
		example = br"""
		\begin{sidebar}{Title}
		\label{sidebar:Basic_Sidebar}
		Body Text
		\end{sidebar}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

		# Check that the DOM has the expected structure
		assert_that( dom.getElementsByTagName('sidebar'), has_length( 1 ) )

		sidebar_el = dom.getElementsByTagName('sidebar')[0]

		# Check that the relatedworkref object has the expected attributes
		assert_that( sidebar_el.ntiid, contains_string( 'tag:nextthought.com,2011-10:testing-Sidebar-temp.sidebar.sidebar_Basic_Sidebar' ) )

	def test_sidebar_flat(self):
		example = br"""
		\begin{flatsidebar}{Title}
		\label{sidebar:Flat_Sidebar}
		Body Text
		\end{flatsidebar}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

		# Check that the DOM has the expected structure
		assert_that( dom.getElementsByTagName('flatsidebar'), has_length( 1 ) )

		sidebar_el = dom.getElementsByTagName('flatsidebar')[0]

		# Check that the relatedworkref object has the expected attributes
		assert_that( sidebar_el.attributes.get('title').source, contains_string( 'Title' ) )
		assert_that( sidebar_el.childNodes[2].source, contains_string( 'Body Text' ) )

	def test_sidebar_graphic(self):
		example = br"""
		\begin{ntigraphicsidebar}{Title}{testing}
		\label{sidebar:Graphic_Sidebar}
		Body Text
		\end{ntigraphicsidebar}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

		# Check that the DOM has the expected structure
		assert_that( dom.getElementsByTagName('ntigraphicsidebar'), has_length( 1 ) )

		sidebar_el = dom.getElementsByTagName('ntigraphicsidebar')[0]

		# Check that the relatedworkref object has the expected attributes
		assert_that( sidebar_el.attributes.get('title').source, contains_string( 'Title' ) )
		assert_that( sidebar_el.attributes.get('graphic_class'), contains_string( 'testing' ) )
		assert_that( sidebar_el.childNodes[2].source, contains_string( 'Body Text' ) )

