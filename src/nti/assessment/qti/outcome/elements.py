# -*- coding: utf-8 -*-
"""
Defines a QTI assesments element

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as out_interfaces

@qti_creator
@interface.implementer(out_interfaces.IoutcomeProcessing)
class OutcomeProcessing(QTIElement):
	pass

@qti_creator
@interface.implementer(out_interfaces.IoutcomeIf)
class OutcomeIf(QTIElement):
	pass

@qti_creator
@interface.implementer(out_interfaces.IoutcomeElseIf)
class OutcomeElseIf(QTIElement):
	pass

@qti_creator
@interface.implementer(out_interfaces.IoutcomeElse)
class OutcomeElse(QTIElement):
	pass

@qti_creator
@interface.implementer(out_interfaces.IoutcomeCondition)
class OutcomeCondition(QTIElement):
	pass

@qti_creator
@interface.implementer(out_interfaces.IexitTest)
class ExitTest(QTIElement):
	pass

