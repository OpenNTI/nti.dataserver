#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nti.tests import ConfiguringTestBase, is_true, is_false

from zope import interface
from zope import component

import nti.assessment
from nti.assessment import response, solution
from nti.assessment import interfaces
from nti.assessment._latexplastexdomcompare import _mathChildIsEqual as mce


class TestLatex(ConfiguringTestBase):

	set_up_packages = (nti.assessment,)

	def test_simple_grade(self):

		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$" )

		rsp = response.QTextResponse( soln.value )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )

		assert_that( soln.grade( soln.value ), is_true() )

	def test_simple_grade_with_numeric_parens(self):
		# We don't get it right, but we don't blow up either
		soln = solution.QLatexSymbolicMathSolution( r"$6$" )

		rsp = response.QTextResponse(  r"$3(2)$" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )


	def test_simple_grade_accept_trailing_units(self):
		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$" )

		rsp = response.QTextResponse( soln.value + " day" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		### FIXME FIXME FIXME:
		# See _latexplastexconverter. There's apparently some global state
		# in the plasTeX package we haven't yet gotten rid of.
		# If we run this test case, then a bunch of the content rendering tests fail because something
		# isn't getting cleaned up like it should.
		# To demonstrate, uncomment the two assertions, and run the following command:
		# nosetests nti.assessment.tests.test_latex:TestLatex.test_simple_grade_accept_trailing_units nti.contentrendering.resources.tests.test_resourcedb:TestResourceDBTabular.test_system_generate
		# TestResourceDBTabular will fail
		#assert_that( grader(  ), is_true() )
		#assert_that( soln.grade( soln.value ), is_true() )

	def test_simple_grade_accept_trailing_percent(self):

		soln = solution.QLatexSymbolicMathSolution( "$75$" )

		rsp = response.QTextResponse( r"$75 \%$" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_true() )

		assert_that( soln.grade( soln.value ), is_true() )

	def test_grade_empty(self):
		rsp = response.QTextResponse( "" )
		soln = solution.QLatexSymbolicMathSolution( r"$\frac{1}{2}$" )

		grader = component.getMultiAdapter( (None, soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader(  ), is_false() )

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
