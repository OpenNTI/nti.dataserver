# -*- coding: utf-8 -*-
"""
Defines QTI template interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from ..qti import interfaces as qti_interfaces
from ..basic import interfaces as basic_interfaces
from ..content import interfaces as cnt_interfaces
from ..variables import interfaces as var_interfaces
from ..expression import interfaces as exp_interfaces
from ..attributes import interfaces as attr_interfaces
	
class ItemplateDeclaration(var_interfaces.IvariableDeclaration, attr_interfaces.ItemplateDeclarationAttrGroup, qti_interfaces.IConcrete):
	pass

class ItemplateElement(basic_interfaces.IbodyElement, attr_interfaces.ItemplateElementAttrGroup):
	pass

class ItemplateBlock(cnt_interfaces.IblockStatic, cnt_interfaces.IflowStatic, ItemplateElement, IFiniteSequence, qti_interfaces.IConcrete):
	blockStatic = schema.List(schema.Object(cnt_interfaces.IblockStatic), "The ordered list of blockStatic elements", min_length=0)

class ItemplateInline(cnt_interfaces.IflowStatic, cnt_interfaces.IinlineStatic, ItemplateElement, IFiniteSequence, qti_interfaces.IConcrete):
	inlineStatic = schema.List(schema.Object(cnt_interfaces.IinlineStatic), "The ordered list of inlineStatic elements", min_length=0)

class IintegerOrVariableRef(interface.Interface, qti_interfaces.IConcrete):
	pass
	
class IfloatOrVariableRef(interface.Interface, qti_interfaces.IConcrete):
	pass
	
class IstringOrVariableRef(interface.Interface, qti_interfaces.IConcrete):
	pass
	
class ItemplateRule(interface.Interface):
	pass
	
class ItemplateProcessing(interface.Interface, qti_interfaces.IConcrete):
	templateRule = schema.List(schema.Object(ItemplateRule), title="The ordered list of templateRule elements", min_length=1)

class templateConstraint (ItemplateRule, IFiniteSequence, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(exp_interfaces.Iexpression), title="The expressions", min_length=0)

class ItemplateIf(interface.Interface, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)
	templateRule = schema.List(schema.Object(ItemplateRule), title="The ordered list of templateRule elements", min_length=0)
	
class ItemplateElseIf(interface.Interface, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)
	templateRule = schema.List(schema.Object(ItemplateRule), title="The ordered list of templateRule elements", min_length=0)
	
class ItemplateElse(interface.Interface, qti_interfaces.IConcrete):
	templateRule = schema.List(schema.Object(ItemplateRule), title="The ordered list of templateRule elements", min_length=0)
	
class ItemplateCondition(ItemplateRule, qti_interfaces.IConcrete):
	templateIf = schema.Object(ItemplateIf, title='The templateIf', required=True)
	templateElseIf =  schema.List(schema.Object(ItemplateElseIf), title='The order list of templateIf elements', min_length=0)
	templateElse =  schema.Object(ItemplateElse, title='The templateElse elements', required=False)
	
class IsetTemplateValue(ItemplateRule, attr_interfaces.IsetTemplateValueAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)
	
class IsetCorrectResponse(ItemplateRule, attr_interfaces.IsetCorrectResponseAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)

class IsetDefaultValue(ItemplateRule, attr_interfaces.IsetDefaultValueAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)	

class IexitTemplate(ItemplateRule, qti_interfaces.IConcrete):
	pass



