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

from ..ntiassessment import naquestion, naquestionset

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
			\naqsolution $420$
			\naqsolution $\frac{5}{8}$
			\naqsolution $\left(3x+2\right)\left(2x+3\right)$
			\naqsolution $\surd2$
			\naqsolution $\frac{\surd\left(8x+5\right)\left(12x+12\right)}{\approx152318}+1204$
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
	values 	=  ['420',
				r'\frac{5}{8}',
				'\\left(3x+2\\right)\\left(2x+3\\right)',
				'\\surd 2',
				'\\frac{\\surd \\left(8x+5\\right)\\left(12x+12\\right)}{\\approx 152318}+1204']
	for index,item in enumerate(getattr( part_el, '_asm_solutions' )()):
		assert_that( item, verifiably_provides( part_el.soln_interface ) )
		assert_that( item, has_property( 'weight', 1.0 ) )
		assert_that( item, has_property( 'value', values[index] ) )

	part = part_el.assessment_object()
	assert_that( part, verifiably_provides( part_el.part_interface ) )
	assert_that( part.content, is_( "Arbitrary content goes here." ) )
	assert_that( part.hints, has_length( 1 ) )
	assert_that( part.hints, contains( verifiably_provides( asm_interfaces.IQHint ) ) )

def test_question_set_macros():
	example = br"""
	\begin{naquestion}[individual=true]
		\label{question}
		Arbitrary content goes here.
		\begin{naqsymmathpart}
		Arbitrary content goes here.
		\begin{naqsolutions}
			\naqsolution $420$
			\naqsolution $\frac{5}{8}$
			\naqsolution $\left(3x+2\right)\left(2x+3\right)$
			\naqsolution $\surd2$
			\naqsolution $\frac{\surd\left(8x+5\right)\left(12x+12\right)}{\approx152318}+1204$
		\end{naqsolutions}
		\begin{naqhints}
			\naqhint Some hint
		\end{naqhints}
		\end{naqsymmathpart}
	\end{naquestion}

	\begin{naquestionset}
		\label{set}
		\naquestionref{question}
	\end{naquestionset}

	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	assert_that( dom.getElementsByTagName('naquestion'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestion')[0], is_( naquestion ) )

	assert_that( dom.getElementsByTagName('naquestionset'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestionset')[0], is_( naquestionset ) )

	qset_object = dom.getElementsByTagName( 'naquestionset' )[0].assessment_object()
	assert_that( qset_object.questions, has_length( 1 ) )
	assert_that( qset_object.ntiid, contains_string( 'set' ) )

def test_content_adaptation():
	doc = br"""
	\begin{naquestion}[individual=true]
		\begin{naqsymmathpart}
		%s
		\begin{naqsolutions}
			\naqsolution Hello
		\end{naqsolutions}
		\end{naqsymmathpart}
	\end{naquestion}
	"""
	def assert_content(content, output):
		dom = _buildDomFromString( _simpleLatexDocument( (doc % content,) ) )
		naq = dom.getElementsByTagName('naquestion')[0]
		part_el = naq.getElementsByTagName( 'naqsymmathpart' )[0]
		part = part_el.assessment_object()
		assert_that( part, verifiably_provides( part_el.part_interface ) )
		assert_that( part.content, is_( output ) )

	assert_content("Arbitrary content goes here.","Arbitrary content goes here.")
	assert_content( br"Equation: $123 \times 456$.","Equation: ." ) # Fails currently
	assert_content( br"Complex object \begin{tabular}{cc} \\ 1 & 2 \\3 & 4\\ \end{tabular}",
					br"Complex object" ) # Fails currently
	assert_content( br"Figure \begin{figure}[htbp]\begin{center}\includegraphics[width=100px]{images/wu1_square=3=by=x-2.pdf}\end{center}\end{figure}", br"Figure" ) # Fails currently


def test_free_response_macros():
	example = br"""
	\begin{naquestion}[individual=true]
		Arbitrary content goes here.
		\begin{naqfreeresponsepart}
		Arbitrary content goes here.
		\begin{naqsolutions}
			\naqsolution This is a solution.
				It may require multiple lines.

				It may span paragraphs.
			\naqsolution This is another solution.
			\naqsolution In some cases, \textit{it} may be complicated: $i$.

		\end{naqsolutions}
		\begin{naqhints}
			\naqhint Some hint
		\end{naqhints}
		\end{naqfreeresponsepart}
	\end{naquestion}
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	assert_that( dom.getElementsByTagName('naquestion'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestion')[0], is_( naquestion ) )
	naq = dom.getElementsByTagName('naquestion')[0]
	part_el = naq.getElementsByTagName( 'naqfreeresponsepart' )[0]

	part = part_el.assessment_object()
	assert_that( part, verifiably_provides( part_el.part_interface ) )
	assert_that( part.content, is_( "Arbitrary content goes here." ) )
	assert_that( part.solutions[0], has_property( "value", "This is a solution. It may require multiple lines. It may span paragraphs." ) )






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

def test_matching_macros():
	example = br"""
		\begin{naquestion}
			\begin{naqmatchingpart}
			In Rome, women used hair color to indicate their class in society. Match the correct shade with its corresponding class:
				\begin{tabular}{cc}
					Noblewomen & Black \\
					Middle-class & Red \\
					Poor women & Blond \\
				\end{tabular}
				\begin{naqmlabels}
					\naqmlabel[2] Noblewomen
					\naqmlabel[0] Middle-class
					\naqmlabel[1] Poor women
				\end{naqmlabels}
				\begin{naqmvalues}
				   \naqmvalue Black
				   \naqmvalue Red
				   \naqmvalue Blond
				\end{naqmvalues}
			\end{naqmatchingpart}
		\end{naquestion}
		"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	assert_that( dom.getElementsByTagName('naquestion'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('naquestion')[0], is_( naquestion ) )

	assert_that( dom.getElementsByTagName('naqmlabel'), has_length( 3 ) )
	assert_that( dom.getElementsByTagName('naqmvalue'), has_length( 3 ) )


	naq = dom.getElementsByTagName('naquestion')[0]
	part_el = naq.getElementsByTagName( 'naqmatchingpart' )[0]
	soln = getattr( part_el, '_asm_solutions' )()[0]


	assert_that( soln, verifiably_provides( part_el.soln_interface ) )
	assert_that( soln, has_property( 'value', {0: 2, 1: 0, 2: 1} ) )
	assert_that( soln, has_property( 'weight', 1.0 ) )

	part = part_el.assessment_object()
	assert_that( part, verifiably_provides( part_el.part_interface ) )
	assert_that( part, has_property( 'labels', has_length( 3 ) ) )
	assert_that( part.labels, has_item( 'Noblewomen' ) )
	assert_that( part, has_property( 'values', has_length( 3 ) ) )
	assert_that( part.values, has_item( 'Black' ) )

from plasTeX.Renderers.XHTML import Renderer
from nti.contentrendering.plastexpackages import interfaces
from zope import component
from zope import interface
from nti.contentrendering import interfaces as cdr_interfaces
from nti.contentrendering.resources import ResourceRenderer

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

		\begin{naquestionset}\label{testset}
			\naquestionref{testquestion}
		\end{naquestionset}
		"""

		with RenderContext(_simpleLatexDocument( (example,) )) as ctx:
			dom  = ctx.dom
			dom.getElementsByTagName( 'document' )[0].filenameoverride = 'index'
			render = Renderer()
			render.renderableClass = ResourceRenderer.Renderable
			render.importDirectory( os.path.join( os.path.dirname(__file__), '..' ) )
			render.render( dom )

			rendered_book = _MockRenderedBook()
			rendered_book.document = dom
			rendered_book.contentLocation = ctx.docdir

			extractor = component.getAdapter( rendered_book, interfaces.IAssessmentExtractor )
			extractor.transform( rendered_book )

			jsons = open(os.path.join( ctx.docdir, 'assessment_index.json' ), 'rU' ).read()
			obj = json.loads( jsons )

			exp_value = {'Items': {'tag:nextthought.com,2011-10:testing-HTML-temp.0': {'AssessmentItems': {},
						   'Items': {'tag:nextthought.com,2011-10:testing-HTML-temp.chapter_one': {'AssessmentItems': {},
							 'Items': {'tag:nextthought.com,2011-10:testing-HTML-temp.section_one': {'AssessmentItems': {'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion': {'Class': 'Question',
								 'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion',
								 'content': '<a name="testquestion"></a> Arbitrary content goes here.',
								 'parts': [{'Class': 'SymbolicMathPart',
								   'content': 'Arbitrary content goes here.',
								   'explanation': '',
								   'hints': [{'Class': 'HTMLHint',
									 'value': '<a name="a1e8744a89e9bf4e115903c4322d92e1" ></a>\n<p class="par" id="a1e8744a89e9bf4e115903c4322d92e1">Some hint </p>'}],
								   'solutions': [{'Class': 'LatexSymbolicMathSolution',
									 'value': 'Some solution',
									 'weight': 1.0}]}]},
								'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testset': {'Class': 'QuestionSet',
								 'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testset',
								 'questions': [{'Class': 'Question',
								   'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion',
								   'content': '<a name="testquestion"></a> Arbitrary content goes here.',
								   'parts': [{'Class': 'SymbolicMathPart',
									 'content': 'Arbitrary content goes here.',
									 'explanation': '',
									 'hints': [{'Class': 'HTMLHint',
									   'value': '<a name="a1e8744a89e9bf4e115903c4322d92e1" ></a>\n<p class="par" id="a1e8744a89e9bf4e115903c4322d92e1">Some hint </p>'}],
									 'solutions': [{'Class': 'LatexSymbolicMathSolution',
									   'value': 'Some solution',
									   'weight': 1.0}]}]}]}},
							   'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.section_one',
							   'filename': 'tag_nextthought_com_2011-10_testing-HTML-temp_section_one.html',
							   'href': 'tag_nextthought_com_2011-10_testing-HTML-temp_section_one.html'}},
							 'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.chapter_one',
							 'filename': 'tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html',
							 'href': 'tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html'}},
						   'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.0',
						   'filename': 'index.html',
						   'href': 'index.html'}},
						 'filename': 'index.html',
						 'href': 'index.html'}
			assert_that( obj, is_( exp_value ) )
