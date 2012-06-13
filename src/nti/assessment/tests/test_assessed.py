#!/usr/bin/env python
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_entry, is_, has_property, contains
from nti.tests import ConfiguringTestBase, is_true, is_false
from nti.tests import verifiably_provides
from nti.externalization.tests import externalizes
from nose.tools import assert_raises

from zope import interface
from zope import component
from zope.schema import interfaces as sch_interfaces

import nti.assessment
from nti.externalization.internalization import update_from_external_object

from nti.assessment import interfaces
from nti.assessment import parts
from nti.assessment import response
from nti.assessment import submission
from nti.assessment import assessed
from nti.assessment import solution as solutions


#pylint: disable=R0904

class TestAssessedPart(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_externalizes(self):
		assert_that( assessed.QAssessedPart(), verifiably_provides( interfaces.IQAssessedPart ) )
		assert_that( assessed.QAssessedPart(), externalizes( has_entry( 'Class', 'AssessedPart' ) ) )

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


class TestAssessedQuestionSet(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_externalizes(self):
		assert_that( assessed.QAssessedQuestionSet(), verifiably_provides( interfaces.IQAssessedQuestionSet ) )
		assert_that( assessed.QAssessedQuestionSet(), externalizes( has_entry( 'Class', 'AssessedQuestionSet' ) ) )
