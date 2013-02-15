#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from zope import interface

from nti.assessment.qti.basic.element import qti_creator
from nti.assessment.qti.expression import interfaces as exp_interfaces

from nti.assessment.qti.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, none, has_property )
		
class TestBasicElement(ConfiguringTestBase):
	
	def test_simple_object(self):
		
		@qti_creator
		@interface.implementer(exp_interfaces.IintegerToFloat)
		class Foo(object):
			pass
		
		@interface.implementer(exp_interfaces.Iexpression)
		class Exp(object):
			pass 
		
		assert_that(Foo, has_property('_v_definitions'))
		assert_that(Foo, has_property('expression'))
		
		f = Foo()
		e = Exp()
		f.expression = e
		assert_that(f.expression, is_(e))
		f.expression = None
		assert_that(f.expression, is_(none()))
		
		try:
			f.expression = 'test'
			self.fail('Was able to set invalid value')
		except:
			pass

	def test_simple_list(self):
		
		@qti_creator
		@interface.implementer(exp_interfaces.Imax)
		class Foo(object):
			pass
		
		@interface.implementer(exp_interfaces.Iexpression)
		class Exp(object):
			pass 
		
		f = Foo()
		e = Exp()
		assert_that(f.expression, is_([]))
		f.add_expression(e)
		assert_that(f.expression, is_([e]))
		assert_that(f.get_expression_list(), is_([e]))
	
if __name__ == '__main__':
	unittest.main()
	
