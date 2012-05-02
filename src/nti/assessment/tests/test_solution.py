#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_
from nti.tests import ConfiguringTestBase, is_true, is_false

from zope import interface

import nti.assessment
from nti.assessment import solution, response
from nti.assessment import interfaces

class TestConvert(ConfiguringTestBase):

	set_up_packages = (nti.assessment,)

	def test_not_isolution(self):
		assert_that( interfaces.convert_response_for_solution( self, self ), is_( self ) )
		# Because we have no interfaces, no conversion is attempted
		assert_that( interfaces.convert_response_for_solution( self, 42 ), is_( 42 ) )


	def test_convert_fails(self):
		class Soln(object):
			interface.implements(interfaces.IQMathSolution)

		assert_that( interfaces.convert_response_for_solution( Soln(), self ), is_( self ) )
		assert_that( interfaces.convert_response_for_solution( Soln(), self.set_up_packages ), is_( self.set_up_packages ) )

	def test_convert_from_string(self):
		class Soln(object):
			interface.implements(interfaces.IQMathSolution)

		assert_that( interfaces.convert_response_for_solution( Soln(), "string" ), is_( response.QTextResponse ) )

	def test_convert_from_number(self):
		class Soln(object):
			interface.implements(interfaces.IQNumericMathSolution)

		assert_that( interfaces.convert_response_for_solution( Soln(), 42 ), is_( response.QTextResponse ) )

class TestNumericMathSolution(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)
	def test_grade_numbers(self):
		assert_that( solution.QNumericMathSolution( 1 ).grade( "1" ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1.0 ).grade( "1" ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1.0 ).grade( "1.0" ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1 ).grade( "1.0" ), is_true( ) )
		# via number-to-text-solution-to-number
		assert_that( solution.QNumericMathSolution( 1 ).grade( 1 ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1 ).grade( 1.2 ), is_false( ) )

class TestFreeResponseSolution(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)
	def test_grade_string(self):
		assert_that( solution.QFreeResponseSolution( "text" ).grade( "text" ), is_true( ) )

		# Case sensitive at the moment
		assert_that( solution.QFreeResponseSolution( "text" ).grade( "Text" ), is_false( ) )
