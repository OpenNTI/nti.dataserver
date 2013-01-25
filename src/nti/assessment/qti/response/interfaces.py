from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.outcome import interfaces as out_interfaces
from nti.assessment.qti.expression import interfaces as exp_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

# generalized response processing

class IresponseRule(interface.Interface):
	pass
	
class IresponseProcessing(attr_interfaces.IresponseProcessingAttrGroup, IFiniteSequence):
	__display_name__ = "responseProcessing"
	value = schema.List(IresponseRule, title="An ordered list of values", min_length=1)

class IresponseIf(IresponseRule):
	__display_name__ = "responseIf"
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	responseRule = schema.List(IresponseRule, title='The ordered response rules', required=False, min_length=0)
	
class IresponseElseIf(IresponseRule):
	__display_name__ = "responseElseIf"
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)
	responseRule = schema.List(IresponseRule, title='The ordered response rules', required=False, min_length=0)
	
class IresponseElse(IresponseRule):
	__display_name__ = "responseElse"
	responseRule = schema.List(IresponseRule, title='The ordered response rules', required=False, min_length=0)
	
class IresponseCondition(IresponseRule):
	__display_name__ = "responseCondition"
	responseIf = schema.Object(IresponseIf, title='response if', required=True)
	responseElseIf = schema.List(IresponseElseIf, title='response if list', required=False, min_length=0)
	responseElse = schema.Object(IresponseElse, title='response else', required=False)

class IsetOutcomeValue(out_interfaces.IoutcomeRule, IresponseRule, attr_interfaces.IsetOutcomeValueAttrGroup):
	__display_name__ = "setOutcomeValue"
	expression = schema.Object(exp_interfaces.Iexpression, title='The expression', required=True)

class IlookupOutcomeValue(out_interfaces.IoutcomeRule, IresponseRule, attr_interfaces.IlookupOutcomeValueAttrGroup):
	__display_name__ = "lookupOutcomeValue"
	expression = schema.Object(exp_interfaces.Iexpression, title='A single cardinality expression', required=True)
	
class IexitResponse(IresponseRule):
	__display_name__ = "exitResponse"

	