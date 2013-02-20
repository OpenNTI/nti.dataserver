# -*- coding: utf-8 -*-
"""
Defines QTI template element

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as tmp_interfaces

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateDeclaration)
class TemplateDeclaration(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateBlock)
class TemplateBlock(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateInline)
class TemplateInline(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.IintegerOrVariableRef)
class IntegerOrVariableRef(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.IfloatOrVariableRef)
class FloatOrVariableRef(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.IstringOrVariableRef)
class StringOrVariableRef(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateProcessing)
class TemplateProcessing(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateConstraint)
class TemplateConstraint(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateIf)
class TemplateIf(QTIElement):
	pass
	
@qti_creator
@interface.implementer(tmp_interfaces.ItemplateElseIf)
class TemplateElseIf(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateElse)
class TemplateElse(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.ItemplateCondition)
class TemplateCondition(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.IsetTemplateValue)
class SetTemplateValue(QTIElement):
	pass
	
@qti_creator
@interface.implementer(tmp_interfaces.IsetCorrectResponse)
class SetCorrectResponse(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.IsetDefaultValue)
class SetDefaultValue(QTIElement):
	pass

@qti_creator
@interface.implementer(tmp_interfaces.IexitTemplate)
class ExitTemplate(QTIElement):
	pass
