#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, is_not
from hamcrest import has_entry
from nti.tests import ConfiguringTestBase, is_true, is_false

from nti.tests import verifiably_provides

from zope import interface

import nti.assessment
from nti.assessment import solution, response
from nti.assessment import interfaces


from nti.externalization.externalization import toExternalObject
from nti.externalization import internalization
from nti.externalization.internalization import update_from_external_object


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
		assert_that( solution.QNumericMathSolution( 1 ), verifiably_provides( interfaces.IQNumericMathSolution ) )

		assert_that( solution.QNumericMathSolution( 1 ).grade( "1" ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1.0 ).grade( "1" ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1.0 ).grade( "1.0" ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1 ).grade( "1.0" ), is_true( ) )
		# via number-to-text-solution-to-number
		assert_that( solution.QNumericMathSolution( 1 ).grade( 1 ), is_true( ) )
		assert_that( solution.QNumericMathSolution( 1 ).grade( 1.2 ), is_false( ) )

	def test_grade_units( self ):
		forbidden = solution.QNumericMathSolution( 1, () )
		required = solution.QNumericMathSolution( 1, ('cm',) )
		optional = solution.QNumericMathSolution( 1, ('cm', '' ) )

		assert_that( forbidden, grades_right( "1" ) )
		assert_that( forbidden, grades_right( " 1.0 " ) )
		assert_that( forbidden, grades_right( "1.0" ) )
		assert_that( forbidden, grades_wrong( "1 cm" ) )
		assert_that( forbidden, grades_wrong( "1.0cm" ) )

		assert_that( required, grades_wrong( "1" ) )
		assert_that( required, grades_wrong( " 1.0 " ) )
		assert_that( required, grades_wrong( "1.0" ) )
		assert_that( required, grades_right( "1 cm" ) )
		assert_that( required, grades_right( "1.0cm" ) )

		assert_that( optional, grades_right( "1" ) )
		assert_that( optional, grades_right( " 1.0 " ) )
		assert_that( optional, grades_right( "1.0" ) )
		assert_that( optional, grades_right( "1 cm" ) )
		assert_that( optional, grades_right( "1.0cm" ) )

	def test_external_units( self ):
		default = solution.QNumericMathSolution( 1 )
		forbidden = solution.QNumericMathSolution( 1, () )
		required = solution.QNumericMathSolution( 1, ('cm',) )
		optional = solution.QNumericMathSolution( 1, ('cm', '' ) )

		ext = toExternalObject( default )
		assert_that( ext, has_entry( 'allowed_units', None ) )

		ext = toExternalObject( forbidden )
		assert_that( ext, has_entry( 'allowed_units', [] ) )

		ext = toExternalObject( required )
		assert_that( ext, has_entry( 'allowed_units', ['cm'] ) )

		ext = toExternalObject( optional )
		assert_that( ext, has_entry( 'allowed_units', ['cm', ''] ) )


	def test_equality( self ):
		soln = solution.QNumericMathSolution( 1 )
		soln2 = solution.QNumericMathSolution( 1 )
		soln3 = solution.QNumericMathSolution( 2 )

		soln4 = solution.QNumericMathSolution( 1 )
		soln4.weight = 0.5

		assert_that( soln, is_( soln2 ) )
		assert_that( soln, is_not( soln3 ) )
		assert_that( soln, is_not( soln4 ) )
		assert soln != soln4 # hit the ne operator


class TestFreeResponseSolution(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)
	def test_grade_string(self):
		assert_that( solution.QFreeResponseSolution( "text" ).grade( "text" ), is_true( ) )

		# SAJ: We are now not case sensitive
		assert_that( solution.QFreeResponseSolution( "text" ).grade( "Text" ), is_true( ) )


class TestMultipleChoiceMultipleAnswerSolution(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)
	def test_multiplechoicemultipleanswersolution(self):
		assert_that( solution.QMultipleChoiceMultipleAnswerSolution( [ 1 ] ), grades_correct( [ 1 ] ) )
		assert_that( solution.QMultipleChoiceMultipleAnswerSolution( [ 1, 2 ] ), grades_correct( [ 1, 2 ] ) )
		assert_that( solution.QMultipleChoiceMultipleAnswerSolution( [ 1, 2, 3 ] ), grades_correct( [ 1, 2, 3 ] ) )

		assert_that( solution.QMultipleChoiceMultipleAnswerSolution( [ 1, 2 ] ), grades_wrong( [2, 1] ) )

from hamcrest.core.base_matcher import BaseMatcher

class GradeMatcher(BaseMatcher):
	def __init__( self, value, response ):
		super(GradeMatcher,self).__init__()
		self.value = value
		self.response = response

	def _matches( self, solution ):
		return solution.grade( self.response ) == self.value

	def describe_to( self, description ):
		description.append_text( 'solution that grades ').append_text( str(self.response) ).append_text( ' as ' ).append_text( str(self.value) )

	def describe_mismatch( self, item, mismatch_description ):
		mismatch_description.append_text( 'solution ' ).append_text( str(type(item) ) ).append_text( ' ' ).append_text( str(item) ).append_text( ' graded ' + self.response + ' as ' + str( not self.value ) )

	def __repr__( self ):
		return 'solution that grades as ' + str(self.value)

def grades_correct( response ):
	return GradeMatcher(True, response)
grades_right = grades_correct

def grades_wrong( response ):
	return GradeMatcher(False, response )
