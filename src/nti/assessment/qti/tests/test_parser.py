#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from .. import parser

from . import ConfiguringTestBase
from ..items import AssessmentItem

from hamcrest import (assert_that, is_, is_not, instance_of, has_length, none)

class TestParser(ConfiguringTestBase):

	def test_parse_choice(self):
		path = os.path.join(os.path.dirname(__file__), 'choice.xml')
		with open(path, "r") as f:
			qti = parser.parser(f)

		assert_that(qti, is_not(none()))
		assert_that(qti, instance_of(AssessmentItem))
		assert_that(qti.identifier, is_('choice'))
		assert_that(qti.adaptive, is_(False))
		assert_that(qti.timeDependent, is_(False))
		assert_that(qti.title, is_('Unattended Luggage'))
		assert_that(qti.responseDeclaration, has_length(1))
		assert_that(qti.outcomeDeclaration, has_length(1))
		assert_that(qti.itemBody, is_not(none()))

		rd = qti.responseDeclaration[0]
		assert_that(rd.identifier, is_("RESPONSE"))
		assert_that(rd.cardinality, is_("single"))
		assert_that(rd.baseType, is_('identifier'))
		assert_that(rd.correctResponse, is_not(none()))
		assert_that(rd.correctResponse, has_length(1))

		od = qti.outcomeDeclaration[0]
		assert_that(od.identifier, is_("SCORE"))
		assert_that(od.cardinality, is_("single"))
		assert_that(od.baseType, is_("integer"))

		ib = qti.itemBody
		assert_that(ib, has_length(3))
		assert_that(ib.blocks, has_length(3))

	def test_parse_match(self):
		path = os.path.join(os.path.dirname(__file__), 'match.xml')
		with open(path, "r") as f:
			qti = parser.parser(f)

		assert_that(qti, is_not(none()))
		assert_that(qti, instance_of(AssessmentItem))
		assert_that(qti.identifier, is_('match'))
		assert_that(qti.adaptive, is_(False))
		assert_that(qti.timeDependent, is_(True))
		assert_that(qti.title, is_('Characters and Plays'))
		assert_that(qti.responseDeclaration, has_length(1))
		assert_that(qti.outcomeDeclaration, has_length(1))
		assert_that(qti.itemBody, is_not(none()))

		rd = qti.responseDeclaration[0]
		assert_that(rd.identifier, is_("RESPONSE"))
		assert_that(rd.cardinality, is_("multiple"))
		assert_that(rd.baseType, is_('directedPair'))
		assert_that(rd.correctResponse, is_not(none()))
		assert_that(rd.correctResponse, has_length(4))
		assert_that(rd.mapping, is_not(none()))
		assert_that(rd.mapping.defaultValue, is_(0.0))
		assert_that(rd.mapping, has_length(4))

		od = qti.outcomeDeclaration[0]
		assert_that(od.identifier, is_("SCORE"))
		assert_that(od.cardinality, is_("single"))
		assert_that(od.baseType, is_("float"))

		ib = qti.itemBody
		assert_that(ib, has_length(1))
		assert_that(ib.blocks, has_length(1))

	def test_parse_text_entry(self):
		path = os.path.join(os.path.dirname(__file__), 'text_entry.xml')
		with open(path, "r") as f:
			qti = parser.parser(f)

		assert_that(qti, is_not(none()))
		assert_that(qti, instance_of(AssessmentItem))
		assert_that(qti.identifier, is_('textEntry'))
		assert_that(qti.adaptive, is_(False))
		assert_that(qti.timeDependent, is_(False))
		assert_that(qti.title, is_('Richard III (Take 3)'))
		assert_that(qti.responseDeclaration, has_length(1))
		assert_that(qti.outcomeDeclaration, has_length(1))
		assert_that(qti.itemBody, is_not(none()))

		rd = qti.responseDeclaration[0]
		assert_that(rd.identifier, is_("RESPONSE"))
		assert_that(rd.cardinality, is_("single"))
		assert_that(rd.baseType, is_('string'))
		assert_that(rd.correctResponse, is_not(none()))
		assert_that(rd.correctResponse, has_length(1))
		assert_that(rd.mapping, is_not(none()))
		assert_that(rd.mapping.defaultValue, is_(0.0))
		assert_that(rd.mapping, has_length(2))

		od = qti.outcomeDeclaration[0]
		assert_that(od.identifier, is_("SCORE"))
		assert_that(od.cardinality, is_("single"))
		assert_that(od.baseType, is_("float"))

		ib = qti.itemBody
		assert_that(ib, has_length(2))
		assert_that(ib.blocks, has_length(2))

