# -*- coding: utf-8 -*-
"""
Defines QTI outcome interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from .. import interfaces as qti_interfaces
from ..expression import interfaces as exp_interfaces

class IoutcomeRule(interface.Interface):
	pass
	
class IoutcomeProcessing(interface.Interface, IFiniteSequence, qti_interfaces.IConcrete):
	IoutcomeRule = schema.List(schema.Object(IoutcomeRule), title="Order list of outcome rules", min_length=0)
	
class IoutcomeIf(qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	outcomeRule = schema.List(schema.Object(IoutcomeRule), title='The ordered outcome rules', required=False, min_length=0)
	
class IoutcomeElseIf(qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	outcomeRule = schema.List(schema.Object(IoutcomeRule), title='The ordered outcome rules', required=False, min_length=0)
	
class IoutcomeElse(qti_interfaces.IConcrete):
	outcomeRule = schema.List(schema.Object(IoutcomeRule), title='The ordered outcome rules', required=False, min_length=0)
	
class IoutcomeCondition(qti_interfaces.IConcrete):
	outcomeIf = schema.Object(IoutcomeIf, title='outcome if', required=True)
	outcomeElseIf = schema.List(schema.Object(IoutcomeElseIf), title='outcome if list', required=False, min_length=0)
	outcomeElse = schema.Object(IoutcomeElse, title='outcome else', required=False)
	
class IexitTest(IoutcomeRule, qti_interfaces.IConcrete):
	pass

	