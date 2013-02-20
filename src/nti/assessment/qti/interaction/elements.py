# -*- coding: utf-8 -*-
"""
Defines QTI Interaction elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as int_interfaces

@qti_creator
@interface.implementer(int_interfaces.IendAttemptInteraction)
class EndAttemptInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.Iprompt)
class Prompt(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IgapText)
class GapText(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IgapImg)
class GapImg(QTIElement):
	pass
	
@qti_creator
@interface.implementer(int_interfaces.Igap)
class Gap(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IsimpleAssociableChoice)
class SimpleAssociableChoice(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IsimpleChoice)
class SimpleChoice(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IassociateInteraction)
class AssociateInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IchoiceInteraction)
class ChoiceInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IorderInteraction)
class OrderInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IsimpleMatchSet)
class SimpleMatchSet(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.ImatchInteraction)
class MatchInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IgapMatchInteraction)
class GapMatchInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IinlineChoice)
class InlineChoice(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IinlineChoiceInteraction)
class InlineChoiceInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.ItextEntryInteraction)
class TextEntryInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IextendedTextInteraction)
class ExtendedTextInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IhottextInteraction)
class HottextInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.Ihottext)
class Hottext(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IhotspotChoice)
class HotspotChoice(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IassociableHotspot)
class AssociableHotspot(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IhotspotInteraction)
class HotspotInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IselectPointInteraction)
class SelectPointInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IgraphicOrderInteraction)
class GraphicOrderInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IgraphicAssociateInteraction)
class GraphicAssociateInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IgraphicGapMatchInteraction)
class GraphicGapMatchInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IpositionObjectInteraction)
class PositionObjectInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IpositionObjectStage)
class PositionObjectStage(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IsliderInteraction)
class SliderInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.ImediaInteraction)
class MediaInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IdrawingInteraction)
class DrawingInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IuploadInteraction)
class UploadInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IcustomInteraction)
class CustomInteraction(QTIElement):
	pass

@qti_creator
@interface.implementer(int_interfaces.IinfoControl)
class InfoControl(QTIElement):
	pass
