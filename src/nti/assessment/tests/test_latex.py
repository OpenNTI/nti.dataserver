#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nti.tests import SharedConfiguringTestBase, is_true, is_false
from nti.tests import verifiably_provides
from zope import interface
from zope import component

import nti.assessment
from nti.assessment import response, solution
from nti.assessment import interfaces
from nti.assessment._latexplastexdomcompare import _mathChildIsEqual as mce

from .test_solution import grades_right, grades_wrong

class TestLatex(SharedConfiguringTestBase):

	set_up_packages = (nti.assessment,)

	def test_simple_grade(self):

		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$" )
		assert_that( soln, verifiably_provides( interfaces.IQLatexSymbolicMathSolution ) )

		rsp = response.QTextResponse( soln.value )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )
		assert_that( soln, grades_right( soln.value ) )


	def test_simple_grade_with_numeric_parens(self):
		# We don't get it right, but we don't blow up either
		soln = solution.QLatexSymbolicMathSolution( r"$6$" )

		rsp = response.QTextResponse(  r"$3(2)$" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )


	def test_simple_grade_require_trailing_units(self):
		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$", ('day',) )

		rsp = response.QTextResponse( soln.value + " day" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )
		assert_that( soln, grades_right( soln.value + " day" ) )

		rsp = response.QTextResponse( soln.value )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )
		assert_that( soln, grades_wrong( soln.value ) )

	def test_simple_grade_optional_trailing_units(self):
		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$", ('day','') )

		rsp = response.QTextResponse( soln.value + " day" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )
		assert_that( soln, grades_right( soln.value + " day" ) )

		rsp = response.QTextResponse( soln.value )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )
		assert_that( soln, grades_right( soln.value ) )

	def test_simple_grade_forbids_trailing_units(self):
		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$", () )

		rsp = response.QTextResponse( soln.value + " day" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )
		assert_that( soln, grades_wrong( soln.value + " day" ) )

		rsp = response.QTextResponse( soln.value )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )
		assert_that( soln, grades_right( soln.value ) )

	def test_simple_grade_accept_trailing_percent(self):
		for soln_text in "$75$", "75": # with/out surrounding $

			soln = solution.QLatexSymbolicMathSolution( soln_text )
			assert_that( soln, grades_right( soln_text ) )

			responses = ("75", r"$75 \%$", r"$75\%$", r"75 \%", r"75\%")

			for r in responses:
				rsp = response.QTextResponse( r )
				assert_that( soln, grades_right( rsp ) )

			# With units specified with and without space
			# required
			soln.allowed_units = [u'\uff05'] # full-width percent
			for r in responses[1:]: # the first one can't work, it's missing unit
				rsp = response.QTextResponse( r )
				assert_that( soln, grades_right( rsp ) )

			# optional
			soln.allowed_units.append( '' )
			for r in responses:
				rsp = response.QTextResponse( r )
				assert_that( soln, grades_right( rsp ) )


	def test_grade_empty(self):
		rsp = response.QTextResponse( "" )
		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )

	def test_grade_sympy_parse_problem(self):
		rsp = response.QTextResponse( "'''" ) # Notice an unterminated string
		soln = solution.QLatexSymbolicMathSolution( r"1876" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )

	def test_grade_plastex_parse_problem(self):
		soln = solution.QLatexSymbolicMathSolution(u'16')
		# Seen in real life. The browser's GUI editor makes this relatively
		# easy to construct. Hopefully it can redisplay it, too
		rsp = nti.assessment.response.QTextResponse('\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{1}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}')

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(), is_false() )

	def test_math_child_is_equal_cases(self):
		class MathChild(object):
			OTHER_NODE = 0
			TEXT_NODE = 1
			ELEMENT_NODE = 2
			DOCUMENT_FRAGMENT_NODE = 3

			nodeType = 0
			childNodes = ()
			arguments = ()

			textContent = ''

		child1 = MathChild()
		child2 = MathChild()
		assert_that( mce( child1, child2 ), is_true() )

		# diff types
		child2.nodeType = 4
		assert_that( mce( child1, child2 ), is_false() )

		child2.nodeType = child1.nodeType = child1.ELEMENT_NODE
		# back to equal
		assert_that( mce( child1, child2 ), is_true() )

		# diff arguments
		child2.arguments = (1,)
		assert_that( mce( child1, child2 ), is_false() )

		child2.arguments = ()
		assert_that( mce( child1, child2 ), is_true() )

		# diff child nodes
		child2.childNodes = (MathChild(),)
		assert_that( mce( child1, child2 ), is_false() )
