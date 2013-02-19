#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import os

from .. import elements

from ... import find_concrete_classes
from ... import find_concrete_interfaces

from ...tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length)
		
class TestVariableElements(ConfiguringTestBase):
	
	def test_consistency(self):
		path = os.path.dirname(elements.__file__)
		classes = find_concrete_classes(path)
		interfaces = find_concrete_interfaces(path)
		assert_that(classes, has_length(len(interfaces)))
