#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
from .. import parser

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_not, none)

class TestParser(ConfiguringTestBase):

	def test_parse_choice(self):
		path = os.path.join(os.path.dirname(__file__), 'choice.xml')
		with open(path, "r") as f:
			qti = parser.parser(f)
			assert_that(qti, is_not(none()))

