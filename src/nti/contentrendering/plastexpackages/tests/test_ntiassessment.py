#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals
import os
import shutil
from hamcrest import assert_that, is_, has_length, contains_string

import tempfile
import StringIO

import plasTeX
from plasTeX.TeX import TeX

from ..ntiassessment import naquestion

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import RenderContext

def _simpleLatexDocument(maths):
	return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntiassessment}',),
									bodies=maths )

def test_macros():
	example = br"""
	\begin{naquestion}[individual=true]
		Arbitrary content goes here.
		\begin{naqsymmathpart}
		Arbitrary content goes here.
		\begin{naqsolutions}
			\naqsolution Some solution
		\end{naqsolutions}
		\end{naqsymmathpart}
	\end{naquestion}
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	assert_that( dom.getElementsByTagName('naquestion'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestion')[0], is_( naquestion ) )

def test_multiple_choice_macros():
	example = br"""
			\begin{naquestion}
			Arbitrary prefix content goes here.
			\begin{naqmultiplechoicepart}
			   Arbitrary content for this part goes here.
			   \begin{naqchoices}
			   		\naqchoice Arbitrary content for the choice.
					\naqchoice[1] Arbitrary content for this choice; this is the right choice.
					\naqchoice[0.5] This choice is half correct.
				\end{naqchoices}
				\begin{naqsolexplanation}
					Arbitrary content explaining how the correct solution is arrived at.
				\end{naqsolexplanation}
			\end{naqmultiplechoicepart}
		\end{naquestion}
		"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	assert_that( dom.getElementsByTagName('naquestion'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestion')[0], is_( naquestion ) )

	assert_that( dom.getElementsByTagName('naqchoice'), has_length( 3 ) )
	assert_that( dom.getElementsByTagName('naqsolution'), has_length( 2 ) )



import nti.tests
import nti.contentrendering

class TestRenderableSymMathPart(nti.tests.ConfiguringTestBase):
	set_up_packages = (nti.contentrendering,)

	def _do_test_render( self, label, ntiid, filename='index.html' ):
		from plasTeX.Renderers.XHTML import Renderer
		example = br"""
		\begin{naquestion}[individual=true]%s
			Arbitrary content goes here.
			\begin{naqsymmathpart}
			Arbitrary content goes here.
			\begin{naqsolutions}
				\naqsolution Some solution
			\end{naqsolutions}
			\end{naqsymmathpart}
		\end{naquestion}
		""" % label

		with RenderContext(_simpleLatexDocument( (example,) )) as ctx:
			dom  = ctx.dom
			dom.getElementsByTagName( 'document' )[0].filenameoverride = 'index'
			render = Renderer()
			render.importDirectory( os.path.join( os.path.dirname(__file__), '..' ) )
			render.render( dom )
			# TODO: Actual validation of the rendering


			index = open(os.path.join(ctx.docdir, filename), 'rU' ).read()
			content = """<object type="application/vnd.nextthought.naquestion" data-ntiid="%(ntiid)s" data="%(ntiid)s">\n<param name="ntiid" value="%(ntiid)s" """ % { 'ntiid': ntiid }

			assert_that( index, contains_string( content ) )

	def test_render_id(self):
		self._do_test_render( br'\label{testquestion}', 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion')

	def test_render_counter(self):
		self._do_test_render( b'', 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.1' )
