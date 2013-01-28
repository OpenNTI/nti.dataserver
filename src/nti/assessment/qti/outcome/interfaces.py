from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.expression import interfaces as exp_interfaces

class IoutcomeRule(interface.Interface):
	pass
	
class IoutcomeProcessing(interface.Interface, IFiniteSequence, basic_interfaces.IConcrete):
	IoutcomeRule = schema.List(schema.Object(IoutcomeRule), title="Order list of outcome rules", min_length=0)
	
class IoutcomeIf(basic_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	outcomeRule = schema.List(schema.Object(IoutcomeRule), title='The ordered outcome rules', required=False, min_length=0)
	
class IoutcomeElseIf(basic_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	outcomeRule = schema.List(schema.Object(IoutcomeRule), title='The ordered outcome rules', required=False, min_length=0)
	
class IoutcomeElse(basic_interfaces.IConcrete):
	outcomeRule = schema.List(schema.Object(IoutcomeRule), title='The ordered outcome rules', required=False, min_length=0)
	
class IoutcomeCondition(basic_interfaces.IConcrete):
	outcomeIf = schema.Object(IoutcomeIf, title='outcome if', required=True)
	outcomeElseIf = schema.List(schema.Object(IoutcomeElseIf), title='outcome if list', required=False, min_length=0)
	outcomeElse = schema.Object(IoutcomeElse, title='outcome else', required=False)
	
class Iexitoutcome(IoutcomeRule, basic_interfaces.IConcrete):
	pass

	