from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.variables import interfaces as var_interfaces
from nti.assessment.qti.expression import interfaces as exp_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces
	
class ItemplateDeclaration(var_interfaces.IvariableDeclaration, attr_interfaces.ItemplateDeclarationAttrGroup):
	__display_name__ = "templateDeclaration"

class ItemplateElement(basic_interfaces.IbodyElement, attr_interfaces.ItemplateElementAttrGroup):
	pass

class ItemplateBlock(cnt_interfaces.IblockStatic, cnt_interfaces.IflowStatic, ItemplateElement, IFiniteSequence):
	__display_name__ = "templateBlock"
	blockStatic = schema.List(cnt_interfaces.IblockStatic, "The ordered list of blockStatic elements", min_length=0)

class ItemplateInline(cnt_interfaces.IflowStatic, cnt_interfaces.IinlineStatic, ItemplateElement, IFiniteSequence):
	__display_name__ = "templateInline"
	inlineStatic = schema.List(cnt_interfaces.IinlineStatic, "The ordered list of inlineStatic elements", min_length=0)

class IintegerOrVariableRef(interface.Interface):
	__display_name__ = "integerOrVariableRef"
	
class IfloatOrVariableRef(interface.Interface):
	__display_name__ = "floatOrVariableRef"
	
class IstringOrVariableRef(interface.Interface):
	__display_name__ = "stringOrVariableRef"
	
class ItemplateRule(interface.Interface):
	pass
	
class ItemplateProcessing(interface.Interface):
	__display_name__ = "templateProcessing"
	templateRule = schema.List(ItemplateRule, "The ordered list of templateRule elements", min_length=1)

class templateConstraint (ItemplateRule, IFiniteSequence):
	__display_name__ = 'templateConstraint'
	expression = schema.List(exp_interfaces.Iexpression, "The expressions", min_length=0)

class ItemplateIf(interface.Interface):
	__display_name__ = 'templateIf'
	expression = schema.Object(exp_interfaces.Iexpression, "The expression", required=True)
	templateRule = schema.List(ItemplateRule, "The ordered list of templateRule elements", min_length=0)
	
class ItemplateElseIf(interface.Interface):
	__display_name__ = 'templateElseIf'
	expression = schema.Object(exp_interfaces.Iexpression, "The expression", required=True)
	templateRule = schema.List(ItemplateRule, "The ordered list of templateRule elements", min_length=0)
	
class ItemplateElse(interface.Interface):
	__display_name__ = 'templateElse'
	templateRule = schema.List(ItemplateRule, "The ordered list of templateRule elements", min_length=0)
	
class ItemplateCondition(ItemplateRule):
	__display_name__ = "templateCondition"
	templateIf = schema.Object(ItemplateIf, 'The templateIf', required=True)
	templateElseIf =  schema.List(ItemplateElseIf, 'The order list of templateIf elements', min_length=0)
	templateElse =  schema.Object(ItemplateElse, 'The templateElse elements', required=False)
	
class IsetTemplateValue(ItemplateRule, attr_interfaces.IsetTemplateValueAttrGroup):
	__display_name__ = "setTemplateValue"
	expression = schema.Object(exp_interfaces.Iexpression, "The expression", required=True)
	
class IsetCorrectResponse(ItemplateRule, attr_interfaces.IsetCorrectResponseAttrGroup):
	__display_name__ = "setCorrectResponse"
	expression = schema.Object(exp_interfaces.Iexpression, "The expression", required=True)

class IsetDefaultValue(ItemplateRule, attr_interfaces.IsetDefaultValueAttrGroup):
	__display_name__ = "setDefaultValue"
	expression = schema.Object(exp_interfaces.Iexpression, "The expression", required=True)	

class IexitTemplate(ItemplateRule):
	__display_name__ = "exitTemplate"



