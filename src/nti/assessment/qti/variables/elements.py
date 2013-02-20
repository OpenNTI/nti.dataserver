# -*- coding: utf-8 -*-
"""
Defines QTI variable elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as var_interfaces

@qti_creator
@interface.implementer(var_interfaces.Ivalue)
class Value(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.IdefaultValue)
class DefaultValue(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.ImapEntry)
class MapEntry(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.Imapping)
class Mapping(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.IareaMapEntry)
class AreaMapEntry(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.IareaMapping)
class AreaMapping(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.IcorrectResponse)
class CorrectResponse(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.IresponseDeclaration)
class ResponseDeclaration(QTIElement):
	pass
	
@qti_creator
@interface.implementer(var_interfaces.ImatchTableEntry)
class MatchTableEntry(QTIElement):
	pass

@qti_creator
@interface.implementer(var_interfaces.ImatchTable)
class MatchTable(QTIElement):
	pass
	
@qti_creator
@interface.implementer(var_interfaces.IinterpolationTableEntry)
class InterpolationTableEntry(QTIElement):
	pass
	
@qti_creator
@interface.implementer(var_interfaces.IinterpolationTable)
class InterpolationTable(QTIElement):
	pass
	
@qti_creator
@interface.implementer(var_interfaces.IoutcomeDeclaration)
class OutcomeDeclaration(QTIElement):
	pass
