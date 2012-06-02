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

def _buildDomFromString(docString, mkdtemp=False):
	document = plasTeX.TeXDocument()
	strIO = StringIO.StringIO(docString)
	strIO.name = 'temp'
	tex = TeX(document,strIO)
	document.userdata['jobname'] = 'temp'
	document.userdata['working-dir'] = tempfile.gettempdir() if not mkdtemp else tempfile.mkdtemp()
	document.config['files']['directory'] = document.userdata['working-dir']
	document.config.add_section( "NTI" )
	document.config.set( "NTI", 'provider', 'testing' )
	tex.parse()
	return document

def _simpleLatexDocument(maths):
	doc = br"""\documentclass[12pt]{article} \usepackage{nti.contentrendering.plastexpackages.ntiassessment} \begin{document} """
	mathString = '\n'.join( [str(m) for m in maths] )
	doc = doc + '\n' + mathString + '\n\\end{document}'
	return doc

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

import nti.tests
import nti.contentrendering
class TestRenderable(nti.tests.ConfiguringTestBase):
	set_up_packages = (nti.contentrendering,)
	def test_render(self):
		from plasTeX.Renderers.XHTML import Renderer
		example = br"""
		\begin{naquestion}[individual=true]\label{testquestion}
			Arbitrary content goes here.
			\begin{naqsymmathpart}
			Arbitrary content goes here.
			\begin{naqsolutions}
				\naqsolution Some solution
			\end{naqsolutions}
			\end{naqsymmathpart}
		\end{naquestion}
		"""

		dom = _buildDomFromString( _simpleLatexDocument( (example,) ), mkdtemp=True )
		cwd = os.getcwd()
		try:
			os.chdir(dom.config['files']['directory'])
			render = Renderer()
			render.importDirectory( os.path.join( os.path.dirname(__file__), '..' ) )
			render.render( dom )
			# TODO: Actual validation of the rendering
			index = open(os.path.join(dom.config['files']['directory'],'index.html'), 'rU' ).read()
			content = """<div><p><object type="application/vnd.nextthought.naquestion" data-ntiid="tag:nextthought.com,2011-10:testing-HTML-temp.testquestion" data="tag:nextthought.com,2011-10:testing-HTML-temp.testquestion">\n<param name="ntiid" value="tag:nextthought.com,2011-10:testing-HTML-temp.testquestion" />\n<div class="naquestion">\n\t <span> Arbitrary content goes here. <div class="naquestionpart naqsymmathpart">\n\t <a name="a0000000002"/>\n\t <span> Arbitrary content goes here. <div class="helpdiv hidden"><p>Some solution </p></div>\n<a class="helplink hidden">Solution</a> </span>\n\t <div class="rightwrongbox"></div>\n\t <input class="answerblank" ntitype="naqsymmath" />\n</div> </span>\n\t <a id="submit" class="NTIGreenButton NTISubmitAnswer">Check</a>\n\t <a id="tryagain" class="NTIGreenButton NTITryAgain hidden">Try Again...</a>\n</div>\n</object> </p></div>"""

			assert_that( index, contains_string( content ) )
		finally:
			os.chdir( cwd )
			shutil.rmtree( dom.config['files']['directory'] )
