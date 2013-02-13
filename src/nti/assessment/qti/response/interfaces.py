# -*- coding: utf-8 -*-
"""
Defines QTI response interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from .. import interfaces as qti_interfaces
from ..outcome import interfaces as out_interfaces
from ..expression import interfaces as exp_interfaces
from ..attributes import interfaces as attr_interfaces

# generalized response processing

class IresponseRule(interface.Interface):
	pass
	
class IresponseProcessing(attr_interfaces.IresponseProcessingAttrGroup, IFiniteSequence, qti_interfaces.IConcrete):
	responseRule = schema.List(schema.Object(IresponseRule), title="An ordered list of values", min_length=1)

class IresponseIf(qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	responseRule = schema.List(schema.Object(IresponseRule), title='The ordered response rules', required=False, min_length=0)
	
class IresponseElseIf(qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	responseRule = schema.List(schema.Object(IresponseRule), title='The ordered response rules', required=False, min_length=0)
	
class IresponseElse(qti_interfaces.IConcrete):
	responseRule = schema.List(schema.Object(IresponseRule), title='The ordered response rules', required=False, min_length=0)
	
class IresponseCondition(IresponseRule, qti_interfaces.IConcrete):
	responseIf = schema.Object(IresponseIf, title='response if', required=True)
	responseElseIf = schema.List(schema.Object(IresponseElseIf), title='response if list', required=False, min_length=0)
	responseElse = schema.Object(IresponseElse, title='response else', required=False)

class IsetOutcomeValue(out_interfaces.IoutcomeRule, IresponseRule, attr_interfaces.IsetOutcomeValueAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)

class IlookupOutcomeValue(out_interfaces.IoutcomeRule, IresponseRule, attr_interfaces.IlookupOutcomeValueAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='A single cardinality expression', required=True)
	
class IexitResponse(IresponseRule, qti_interfaces.IConcrete):
	pass

	