# -*- coding: utf-8 -*-
"""
Defines QTI item elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as itms_interfaces

@qti_creator
@interface.implementer(itms_interfaces.IitemSessionControl)
class ItemSessionControl(QTIElement):
	pass

@qti_creator
@interface.implementer(itms_interfaces.IassessmentItem)
class AssessmentItem(QTIElement):
	pass
