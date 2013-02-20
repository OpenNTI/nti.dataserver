# -*- coding: utf-8 -*-
"""
Defines QTI fragment elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as frg_interfaces

@qti_creator
@interface.implementer(frg_interfaces.Iinclude)
class Include(QTIElement):
	pass

@qti_creator
@interface.implementer(frg_interfaces.IresponseProcessingFragment)
class ResponseProcessingFragment(QTIElement):
	pass

@qti_creator
@interface.implementer(frg_interfaces.IoutcomeProcessingFragment)
class OutcomeProcessingFragment(QTIElement):
	pass
