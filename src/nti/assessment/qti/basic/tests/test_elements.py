#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from zope import interface

from nti.assessment.qti.basic.elements import qti_creator
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.expression import interfaces as exp_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

from nti.assessment.qti.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, none, has_property, has_entry, has_length)
		
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
		assert_that(Foo, has_property('_v_attributes'))
		
		assert_that(Foo, has_property('expression'))
		
		f = Foo()
		e = Exp()
		f.expression = e
		assert_that(f.get_attributes(), is_({}))
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
		
	def test_attributes(self):
		
		@qti_creator
		@interface.implementer(exp_interfaces.IrandomFloat)
		class Foo(object):
			pass
		
		f = Foo()
		assert_that(f, has_property('min'))
		assert_that(f, has_property('max'))
		f.min = 0
		f.max = 'maxval'
		assert_that(f.min, is_(0))
		assert_that(f.max, is_('maxval'))
		
		attributes = f.get_attributes()
		assert_that(attributes, has_entry('min', 0))
		assert_that(attributes, has_entry('max', 'maxval'))
	
		@qti_creator
		@interface.implementer(attr_interfaces.IequalAttrGroup)
		class Foo2(object):
			pass
		
		f = Foo2()
		assert_that(f, has_property('toleranceMode'))
		assert_that(f, has_property('tolerance'))
		assert_that(f, has_property('includeLowerBound'))
		assert_that(f, has_property('includeUpperBound'))
		
		f.tolerance = '1 2'
		assert_that(f.tolerance, is_([1,2]))
		f.tolerance = [3,4]
		assert_that(f.tolerance, is_([3,4]))
		
		attributes = f.get_attributes()
		assert_that(attributes, has_length(1))
		
		f.includeLowerBound = True
		f.includeUpperBound = False
		attributes = f.get_attributes()
		assert_that(attributes, has_length(3))
		
		@qti_creator
		@interface.implementer(attr_interfaces.IcustomOperatorAttrGroup)
		class Foo3(object):
			pass
		f = Foo3()
		assert_that(f, has_property('class'))
		assert_that(f, has_property('definition'))
		
	def test_sequence(self):
		@qti_creator
		@interface.implementer(cnt_interfaces.IsimpleInline)
		class Foo(object):
			pass
	
		@interface.implementer(cnt_interfaces.Iinline)
		class Inline(object):
			pass

		f = Foo()
		assert_that(f, has_length(0))
		inl = Inline()
		f.inline.append(inl)
		assert_that(f, has_length(1))
		assert_that(f[0], is_(inl))
	
if __name__ == '__main__':
	unittest.main()
	
