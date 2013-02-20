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
from . import interfaces as pre_interfaces

@qti_creator
@interface.implementer(pre_interfaces.IpreCondition)
class PreCondition(QTIElement):
	pass

@qti_creator
@interface.implementer(pre_interfaces.IbranchRule)
class BranchRule(QTIElement):
	pass
