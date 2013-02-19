#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from .. import find_concrete_classes
from .. import find_concrete_interfaces

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length)

class TestQTIModule(ConfiguringTestBase):
	
	def test_find_concrete_interfaces(self):		
		elements = find_concrete_interfaces()
		assert_that(elements, has_length(220))
		
	def test_find_concrete_classes(self):		
		elements = find_concrete_classes()
		assert_that(elements, has_length(11))

	
