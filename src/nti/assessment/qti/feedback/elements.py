# -*- coding: utf-8 -*-
"""
Defines QTI feedback elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as fbk_interfaces

@qti_creator
@interface.implementer(fbk_interfaces.ImodalFeedback)
class ModalFeedback(QTIElement):
	pass

@qti_creator
@interface.implementer(fbk_interfaces.ItestFeedback)
class TestFeedback(QTIElement):
	pass
