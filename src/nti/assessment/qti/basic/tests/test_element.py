#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from zope import interface

from nti.assessment.qti.basic._element import qti_creator
from nti.assessment.qti.content import interfaces as cnt_interfaces

from nti.assessment.qti.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length)

				
class TestQTIElement(ConfiguringTestBase):
	
	def test_find_concrete_elements(self):
		@qti_creator
		@interface.implementer(cnt_interfaces.IsimpleInline)
		class A(object):
			pass
		
		print(A)

	
if __name__ == '__main__':
	unittest.main()
	
