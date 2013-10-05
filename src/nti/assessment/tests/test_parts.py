#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that, has_entry
from hamcrest import is_, is_not
from unittest import TestCase
from nti.testing.matchers import is_true, is_false
from nti.testing.matchers import verifiably_provides
from nti.externalization.tests import externalizes
from nose.tools import assert_raises

from zope import interface

import nti.assessment

from nti.assessment import interfaces
from nti.assessment import parts
from nti.assessment import solution as solutions

from . import grades_right
from . import grades_wrong


# nose module-level setup
setUpModule = lambda: nti.testing.base.module_setup( set_up_packages=(nti.assessment,) )
tearDownModule = nti.testing.base.module_teardown



class TestQPart(TestCase):

	def test_part_provides(self):
		part = parts.QPart()
		assert_that( part, verifiably_provides( interfaces.IQPart ) )
		assert_that( part, is_( part ) )
		assert_that( part, is_not( parts.QPart( content='other' ) ) )
		# hit the ne operator specifically
		assert part != parts.QPart( content='other' )

	def test_part_badkw(self):
		with assert_raises(TypeError):
			parts.QPart( bad_kw=1 )


class TestMultipleChoicePart(TestCase):

	def test_part_provides(self):
		assert_that( parts.QMultipleChoicePart(), verifiably_provides( interfaces.IQMultipleChoicePart ) )
		assert_that( parts.QMultipleChoicePart(), externalizes( has_entry( 'Class', 'MultipleChoicePart' ) ) )

		# A bad solution type
		part = parts.QMultipleChoicePart( solutions=("foo",) )
		assert_that( part, verifiably_provides( interfaces.IQMultipleChoicePart ) )
		assert_that( part, is_( part ) )

		with assert_raises(interface.Invalid):
			sf = interfaces.IQMultipleChoicePart['solutions']
			sf.bind( part )
			sf.validate( part.solutions )


	def test_grade(self):
		solution = solutions.QMultipleChoiceSolution( 1 )
		choices = ("A", "B", "C")
		part = parts.QMultipleChoicePart( solutions=(solution,), choices=choices )

		# Submitting the actual data
		assert_that( part.grade( "B" ), is_true() )
		assert_that( part.grade( "A" ), is_false() )

		# Submitting the index
		assert_that( part.grade( 1 ), is_true() )
		assert_that( part.grade( 0 ), is_false() )

class TestMultipleChoiceMultipleAnswerPart(TestCase):

	def test_part_provides(self):
		assert_that( parts.QMultipleChoiceMultipleAnswerPart(), verifiably_provides( interfaces.IQMultipleChoiceMultipleAnswerPart ) )
		assert_that( parts.QMultipleChoiceMultipleAnswerPart(), externalizes( has_entry( 'Class', 'MultipleChoiceMultipleAnswerPart' ) ) )

		# A bad solution type
		part = parts.QMultipleChoiceMultipleAnswerPart( solutions=( [ 0, 1 ],) )
		assert_that( part, verifiably_provides( interfaces.IQMultipleChoiceMultipleAnswerPart ) )
		assert_that( part, is_( part ) )

		with assert_raises(interface.Invalid):
			sf = interfaces.IQMultipleChoiceMultipleAnswerPart['solutions']
			sf.bind( part )
			sf.validate( part.solutions )


	def test_grade(self):
		solution = solutions.QMultipleChoiceMultipleAnswerSolution( [ 1 ] )
		choices = ("A", "B", "C")
		part = parts.QMultipleChoiceMultipleAnswerPart( solutions=(solution,), choices=choices )

		# Submitting the index
		assert_that( part.grade( [ 1 ] ), is_true() )
		assert_that( part.grade( [ 0 ] ), is_false() )

class TestMatchingPart(TestCase):

	def test_grade(self):
		labels = ("A","B")
		values = ("X", "Y")

		solution_keys = {"A": "Y", "B": "X"}
		solution_nums = {0: 1, 1: 0}

		solution = solutions.QMatchingSolution( solution_keys )
		part = parts.QMatchingPart( labels=labels, values=values, solutions=(solution,) )
		part2 = parts.QMatchingPart( labels=labels, values=values, solutions=(solution,) )
		assert_that( part, externalizes( has_entry( 'Class', 'MatchingPart') ) )
		assert_that( part, is_( part ) )
		assert_that( part, is_( part2 ) )


		assert_that( part, grades_right( solution_keys ) )
		assert_that( part, grades_right( solution_nums ) )

		assert_that( part, grades_wrong( {"A": "Y"} ) )

		part = parts.QMatchingPart( labels=labels, values=values, solutions=(solutions.QMatchingSolution( solution_nums ),) )

		assert_that( part, grades_right( solution_keys ) )
		assert_that( part, grades_right( solution_nums ) )

		assert_that( part, grades_wrong( {"A": "Y"} ) )

		assert_that( part, grades_wrong( {"A": "Z"} ) )

	def test_eq(self):
		labels = ("A","B")
		values = ("X", "Y")

		solution_keys = {"A": "Y", "B": "X"}

		solution = solutions.QMatchingSolution( solution_keys )
		part = parts.QMatchingPart( labels=labels, values=values, solutions=(solution,) )
		part2 = parts.QMatchingPart( labels=labels, values=values, solutions=(solution,) )

		assert_that( part, is_( part ) )
		assert_that( part, is_( part2 ) )
		assert_that( part, is_not( parts.QMatchingPart( labels=values, values=labels, solutions=(solution,) ) ) )
		assert_that( part, is_not( parts.QNumericMathPart(solutions=(solution,)) ) )
		assert_that( parts.QNumericMathPart(solutions=(solution,)), is_not( part ) )

		# Cover the AttributeError case
		qnp = parts.QNumericMathPart( solutions=(solution,) )
		qnp.grader_interface = part.grader_interface
		assert_that( part, is_not( qnp ) )

		assert_that( hash(part), is_( hash( part2 ) ) )

def test_free_response_part_eq():

	part = parts.QFreeResponsePart()
	part2 = parts.QFreeResponsePart()

	assert_that( part, is_( part ) )
	assert_that( part, is_( part2 ) )

	solution = solutions.QFreeResponseSolution( value="the value" )

	part = parts.QFreeResponsePart( solutions=(solution,) )
	assert_that( part, is_not( part2 ) )

	part2 = parts.QFreeResponsePart( solutions=(solution,) )
	assert_that( part, is_( part2 ) )

	solution2 = solutions.QFreeResponseSolution( value="the value" )
	part2 = parts.QFreeResponsePart( solutions=(solution2,) )
	assert_that( part, is_( part2 ) )

	solution2 = solutions.QFreeResponseSolution( value="not the value" )
	part2 = parts.QFreeResponsePart( solutions=(solution2,) )
	assert_that( part, is_not( part2 ) )

def test_math_part_eq():
	part = parts.QMathPart()
	part2 = parts.QSymbolicMathPart()

	assert_that( part, is_( part ) )
	assert_that( part2, is_( part2 ) )

	assert_that( part, is_not( part2 ) ) # subclasses would be equal to superclass, except for grader_interface
	part2.grader_interface = part.grader_interface
	assert_that( part, is_not( part2 ) ) # Except that the subclass implementation is always called??
	del part2.grader_interface
	assert_that( part2, is_not( part ) )

from .._util import superhash
def test_superhash_iterable():

	assert_that( superhash( [1, 3, 5] ), is_( superhash( [x for x in [1,3,5]] ) ) )

	# TODO: The hash algorithm fails badly with integers
	assert_that( superhash( [1,2] ), is_( superhash( [2, 1] ) ) )
