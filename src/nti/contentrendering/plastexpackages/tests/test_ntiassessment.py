#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals
import os
from hamcrest import assert_that, is_, has_length, contains_string
from hamcrest import has_property
from hamcrest import contains, has_item
from hamcrest import has_entry
import unittest

import anyjson as json

import plasTeX
from plasTeX.TeX import TeX

from ..ntiassessment import naquestion

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import RenderContext

import nti.tests
from nti.externalization.tests import externalizes
from nti.tests import verifiably_provides

import nti.contentrendering
import nti.assessment
from nti.assessment import interfaces as asm_interfaces
import nti.externalization

def _simpleLatexDocument(maths):
	return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntiassessment}',),
									bodies=maths )

# Nose module-level setup and teardown
setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentrendering,nti.assessment,nti.externalization) )
tearDownModule = nti.tests.module_teardown

def test_macros():
	example = br"""
	\begin{naquestion}[individual=true]
		Arbitrary content goes here.
		\begin{naqsymmathpart}
		Arbitrary content goes here.
		\begin{naqsolutions}
			\naqsolution Some solution
		\end{naqsolutions}
		\begin{naqhints}
			\naqhint Some hint
		\end{naqhints}
		\end{naqsymmathpart}
	\end{naquestion}
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	assert_that( dom.getElementsByTagName('naquestion'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestion')[0], is_( naquestion ) )

	naq = dom.getElementsByTagName('naquestion')[0]
	part_el = naq.getElementsByTagName( 'naqsymmathpart' )[0]
	for item in getattr( part_el, '_asm_solutions' )():
		assert_that( item, verifiably_provides( part_el.soln_interface ) )
		assert_that( item, has_property( 'weight', 1.0 ) )
		assert_that( item, has_property( 'value', 'Some solution' ) )

	part = part_el.assessment_object()
	assert_that( part, verifiably_provides( part_el.part_interface ) )
	assert_that( part.content, is_( "Arbitrary content goes here." ) )
	assert_that( part.hints, has_length( 1 ) )
	assert_that( part.hints, contains( verifiably_provides( asm_interfaces.IQHint ) ) )

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


	naq = dom.getElementsByTagName('naquestion')[0]
	part_el = naq.getElementsByTagName( 'naqmultiplechoicepart' )[0]
	solns = getattr( part_el, '_asm_solutions' )()


	assert_that( solns[0], verifiably_provides( part_el.soln_interface ) )
	assert_that( solns[0], has_property( 'weight', 1.0 ) )

	assert_that( solns[1], verifiably_provides( part_el.soln_interface ) )
	assert_that( solns[1], has_property( 'weight', 0.5 ) )

	part = part_el.assessment_object()
	assert_that( part.solutions, is_( solns ) )
	assert_that( part, verifiably_provides( part_el.part_interface ) )
	assert_that( part.content, is_( "Arbitrary content for this part goes here." ) )
	assert_that( part.explanation, is_( "Arbitrary content explaining how the correct solution is arrived at." ) )
	assert_that( part, has_property( 'choices', has_length( 3 ) ) )
	assert_that( part.choices, has_item( 'Arbitrary content for the choice.' ) )


	quest_el = dom.getElementsByTagName('naquestion')[0]
	question = quest_el.assessment_object()
	assert_that( question.content, is_( 'Arbitrary prefix content goes here.' ) )
	assert_that( question.parts, contains( part ) )
	assert_that( question, has_property( 'ntiid', 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.1' ) )

	assert_that( question, externalizes( has_entry( 'NTIID', question.ntiid ) ) )

from plasTeX.Renderers.XHTML import Renderer
from nti.contentrendering.plastexpackages import interfaces
from zope import component
from zope import interface
from nti.contentrendering import interfaces as cdr_interfaces

@interface.implementer(cdr_interfaces.IRenderedBook)
class _MockRenderedBook(object):
	document = None
	contentLocation = None


class TestRenderableSymMathPart(unittest.TestCase):

	def _do_test_render( self, label, ntiid, filename='index.html' ):

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
		"The label for the question becomes part of its NTIID."
		self._do_test_render( br'\label{testquestion}', 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion')

	def test_render_counter(self):
		self._do_test_render( b'', 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.1' )


	def test_assessment_index(self):

		example = br"""
		\chapter{Chapter One}

		We have a paragraph.

		\section{Section One}

		\begin{naquestion}[individual=true]\label{testquestion}
			Arbitrary content goes here.
			\begin{naqsymmathpart}
			Arbitrary content goes here.
			\begin{naqsolutions}
				\naqsolution Some solution
			\end{naqsolutions}
			\begin{naqhints}
				\naqhint Some hint
			\end{naqhints}
			\end{naqsymmathpart}
		\end{naquestion}
		"""

		with RenderContext(_simpleLatexDocument( (example,) )) as ctx:
			dom  = ctx.dom
			dom.getElementsByTagName( 'document' )[0].filenameoverride = 'index'
			render = Renderer()
			render.importDirectory( os.path.join( os.path.dirname(__file__), '..' ) )
			render.render( dom )

			rendered_book = _MockRenderedBook()
			rendered_book.document = dom
			rendered_book.contentLocation = ctx.docdir

			extractor = component.getAdapter( rendered_book, interfaces.IAssessmentExtractor )
			extractor.transform( rendered_book )

			jsons = open(os.path.join( ctx.docdir, 'assessment_index.json' ), 'rU' ).read()
			obj = json.loads( jsons )

			exp_value = {'Items': {'tag:nextthought.com,2011-10:testing-HTML-temp.0': {'filename': 'index.html', 'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.0', 'href': 'index.html', 'AssessmentItems': {}, 'Items': {'tag:nextthought.com,2011-10:testing-HTML-temp.chapter_one': {'filename': 'tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html', 'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.chapter_one', 'href': 'tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html', 'AssessmentItems': {}, 'Items': {'tag:nextthought.com,2011-10:testing-HTML-temp.section_one': {'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.section_one', 'href': 'tag_nextthought_com_2011-10_testing-HTML-temp_section_one.html', 'AssessmentItems': {'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion': {'content': 'Arbitrary content goes here.', 'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion', 'parts': [{'content': 'Arbitrary content goes here.', 'explanation': '', 'solutions': [{'weight': 1.0, 'Class': 'LatexSymbolicMathSolution', 'value': 'Some solution'}], 'Class': 'SymbolicMathPart', 'hints': [{'Class': 'TextHint', 'value': 'Some hint'}]}], 'Class': 'Question'}}, 'filename': 'tag_nextthought_com_2011-10_testing-HTML-temp_section_one.html'}}}}}}, 'href': 'index.html', 'filename': 'index.html'}

			assert_that( obj, is_( exp_value ) )
