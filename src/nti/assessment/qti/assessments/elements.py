# -*- coding: utf-8 -*-
"""
Defines QTI assesment elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as ast_interfaces

@qti_creator
@interface.implementer(ast_interfaces.Iselection)
class Selection(QTIElement):
	pass
	
@qti_creator
@interface.implementer(ast_interfaces.Iordering)
class Ordering(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.ItimeLimits)
class TimeLimits(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.IvariableMapping)
class VariableMapping(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.ItemplateDefault)
class TemplateDefault(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.Iweight)
class Weight(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.IassessmentSection)
class AssessmentSection(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.IassessmentSectionRef)
class AssessmentSectionRef(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.IassessmentItemRef)
class AssessmentItemRef(QTIElement):
	pass
	
@qti_creator
@interface.implementer(ast_interfaces.ItestPart)
class TestPart(QTIElement):
	pass

@qti_creator
@interface.implementer(ast_interfaces.IassessmentTest)
class AssessmentTest(QTIElement):
	pass
