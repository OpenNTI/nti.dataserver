#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nti.tests import ConfiguringTestBase, is_true, is_false
from nti.tests import verifiably_provides
from nose.tools import assert_raises

from zope import interface
from zope import component

import nti.assessment

from nti.assessment import interfaces
from nti.assessment import parts
from nti.assessment import solution as solutions

class TestQPart(ConfiguringTestBase):

	set_up_packages = (nti.assessment,)

	def test_part_provides(self):
		part = parts.QPart()
		assert_that( part, verifiably_provides( interfaces.IQPart ) )

	def test_part_badkw(self):
		with assert_raises(ValueError):
			parts.QPart( bad_kw=1 )


class TestMultipleChoicePart(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_part_provides(self):
		assert_that( parts.QMultipleChoicePart(), verifiably_provides( interfaces.IQMultipleChoicePart ) )

		# A bad solution type
		part = parts.QMultipleChoicePart( solutions=("foo",) )
		assert_that( part, verifiably_provides( interfaces.IQMultipleChoicePart ) )

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

class TestMatchingPart(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_grade(self):
		labels = ("A","B")
		values = ("X", "Y")

		solution_keys = {"A": "Y", "B": "X"}
		solution_nums = {0: 1, 1: 0}

		solution = solutions.QMatchingSolution( solution_keys )
		part = parts.QMatchingPart( labels=labels, values=values, solutions=(solution,) )

		assert_that( part.grade( solution_keys ), is_true() )
		assert_that( part.grade( solution_nums ), is_true() )

		assert_that( part.grade( {"A": "Y"} ), is_false() )

		part = parts.QMatchingPart( labels=labels, values=values, solutions=(solutions.QMatchingSolution( solution_nums ),) )
		assert_that( part.grade( solution_keys ), is_true() )
		assert_that( part.grade( solution_nums ), is_true() )

		assert_that( part.grade( {"A": "Y"} ), is_false() )

		assert_that( part.grade( {"A": "Z"} ), is_false() )
