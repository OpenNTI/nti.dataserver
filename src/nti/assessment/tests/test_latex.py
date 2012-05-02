#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nti.tests import ConfiguringTestBase, is_true #, is_false

from zope import interface
from zope import component

import nti.assessment
from nti.assessment import response, solution
from nti.assessment import interfaces

class TestLatex(ConfiguringTestBase):

	set_up_packages = (nti.assessment,)

	def test_simple_grade(self):

		soln = solution.QLatexSymbolicMathSolution( "$\frac{1}{2}$" )

		rsp = response.QTextResponse( soln.value )

		grader = component.getMultiAdapter( (soln, rsp), interfaces.IQSymbolicMathGrader )
		assert_that( grader.grade( soln, rsp ), is_true() )

		assert_that( soln.grade( soln.value ), is_true() )
