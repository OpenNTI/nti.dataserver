#!/usr/bin/env python
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_entry, is_, has_property, contains
from hamcrest import none
from nti.tests import ConfiguringTestBase, is_true, is_false
from nti.tests import verifiably_provides
from nti.externalization.tests import externalizes
from nose.tools import assert_raises

from zope import interface
from zope import component
from zope.schema import interfaces as sch_interfaces

import nti.assessment
from nti.externalization.externalization import toExternalObject
from nti.externalization import internalization
from nti.externalization.internalization import update_from_external_object

from nti.assessment import interfaces
from nti.assessment import parts
from nti.assessment import response
from nti.assessment import submission
from nti.assessment import assessed
from nti.assessment import solution as solutions
from nti.assessment.question import QQuestion


#pylint: disable=R0904

class TestAssessedPart(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_externalizes(self):
		assert_that( assessed.QAssessedPart(), verifiably_provides( interfaces.IQAssessedPart ) )
		assert_that( assessed.QAssessedPart(), externalizes( has_entry( 'Class', 'AssessedPart' ) ) )
		assert_that( internalization.find_factory_for( toExternalObject( assessed.QAssessedPart() ) ),
					 is_( none() ) )


		# A text value is coerced to the required type
		part = assessed.QAssessedPart()
		update_from_external_object( part, {"submittedResponse": "The text response"}, require_updater=True )

		assert_that( part.submittedResponse, is_( response.QTextResponse( "The text response" ) ) )
		assert_that( part.submittedResponse, verifiably_provides( interfaces.IQTextResponse ) )

class TestAssessedQuestion(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_externalizes(self):
		assert_that( assessed.QAssessedQuestion(), verifiably_provides( interfaces.IQAssessedQuestion ) )
		assert_that( assessed.QAssessedQuestion(), externalizes( has_entry( 'Class', 'AssessedQuestion' ) ) )
		assert_that( internalization.find_factory_for( toExternalObject( assessed.QAssessedQuestion() ) ),
					 is_( none() ) )

	def test_assess( self ):
		part = parts.QFreeResponsePart(solutions=(solutions.QFreeResponseSolution(value='correct'),))
		question = QQuestion( parts=(part,) )
		questions = {1: question}

		sub = submission.QuestionSubmission( questionId=1, parts=('correct',) )

		result = assessed.assess_question_submission( sub, questions )
		assert_that( result, has_property( 'questionId', 1 ) )
		assert_that( result, has_property( 'parts', contains( assessed.QAssessedPart( submittedResponse='correct', assessedValue=1.0 ) ) ) )

class TestAssessedQuestionSet(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_externalizes(self):
		assert_that( assessed.QAssessedQuestionSet(), verifiably_provides( interfaces.IQAssessedQuestionSet ) )
		assert_that( assessed.QAssessedQuestionSet(), externalizes( has_entry( 'Class', 'AssessedQuestionSet' ) ) )
		assert_that( internalization.find_factory_for( toExternalObject( assessed.QAssessedQuestionSet() ) ),
					 is_( none() ) )
