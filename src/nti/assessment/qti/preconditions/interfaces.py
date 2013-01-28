from __future__ import unicode_literals, print_function

from zope import schema

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.expression import interfaces as exp_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class IpreCondition(basic_interfaces.IConcrete):
	"""
	A preCondition is a simple expression attached to an assessmentSection or assessmentItemRef that must evaluate to true if the item is to be presented
	"""
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)

class IbranchRule(attr_interfaces.IbranchRuleAttrGroup, basic_interfaces.IConcrete):
	"""
	A branch-rule is a simple expression attached to an assessmentItemRef, assessmentSection or testPart that is evaluated after the item
	"""
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)