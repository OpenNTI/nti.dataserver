# -*- coding: utf-8 -*-
"""
Defines QTI response elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as rsp_interfaces

@qti_creator
@interface.implementer(rsp_interfaces.IresponseProcessing)
class ResponseProcessing(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IresponseIf)
class ResponseIf(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IresponseElseIf)
class ResponseElseIf(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IresponseElse)
class ResponseElse(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IresponseCondition)
class ResponseCondition(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IsetOutcomeValue)
class SetOutcomeValue(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IlookupOutcomeValue)
class LookupOutcomeValue(QTIElement):
	pass

@qti_creator
@interface.implementer(rsp_interfaces.IexitResponse)
class ExitResponse(QTIElement):
	pass
