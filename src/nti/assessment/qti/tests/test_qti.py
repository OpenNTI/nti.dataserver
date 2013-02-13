#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import unittest

from nti.assessment.qti import find_concrete_elements

from nti.assessment.qti.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length)

class TestQTIModule(ConfiguringTestBase):
	
	def test_find_concrete_elements(self):		
		elements = find_concrete_elements()
		assert_that(elements, has_length(220))
		
if __name__ == '__main__':
	unittest.main()
	
