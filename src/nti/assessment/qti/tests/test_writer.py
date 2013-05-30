#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
from .. import parser
from .. import writer

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_length, has_entry, none)

class TestParser(ConfiguringTestBase):

	def test_write_choice(self):
		path = os.path.join(os.path.dirname(__file__), 'choice.xml')
		with open(path, "r") as f:
			qti = parser.parser(f)

		root = writer.write(qti)
		assert_that(root, is_not(none()))
		assert_that(root, has_length(4))

		attributes = root.attrib
		assert_that(attributes, has_entry('title', "Unattended Luggage"))
		assert_that(attributes, has_entry('identifier', "choice"))
		assert_that(attributes, has_entry('timeDependent', "False"))
		assert_that(attributes, has_entry('adaptive', "False"))

		assert_that(root.xpath("//correctResponse/value/text()"), is_(['ChoiceA']))
		assert_that(root.xpath("//itemBody//img/@src"), is_(["images/sign.png"]))

	def test_write_text_entry(self):
		path = os.path.join(os.path.dirname(__file__), 'text_entry.xml')
		with open(path, "r") as f:
			qti = parser.parser(f)

		root = writer.write(qti)
		assert_that(root, is_not(none()))
		assert_that(root, has_length(4))

		attributes = root.attrib
		assert_that(attributes, has_entry('title', "Richard III (Take 3)"))
		assert_that(attributes, has_entry('identifier', "textEntry"))
		assert_that(attributes, has_entry('timeDependent', "False"))
		assert_that(attributes, has_entry('adaptive', "False"))

		assert_that(root.xpath("count(//responseDeclaration//mapping/mapEntry)"), is_(2))
		assert_that(root.xpath("//itemBody/p/text()"), is_(["Identify the missing word in this famous quote from Shakespeare's Richard III."]))
