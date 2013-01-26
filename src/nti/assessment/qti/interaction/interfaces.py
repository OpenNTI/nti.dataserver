from __future__ import unicode_literals, print_function

from zope import schema
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class Iinteraction(basic_interfaces.IbodyElement, attr_interfaces.IinteractionAttrGroup):
	pass

class IinlineInteraction(cnt_interfaces.Iflow, cnt_interfaces.Iinline, Iinteraction):
	pass

class IendAttemptInteraction(IinlineInteraction, attr_interfaces.IendAttemptInteractionAttrGroup):
	___display_name__ = "endAttemptInteraction"
		
class Iprompt(basic_interfaces.IbodyElement, IFiniteSequence):
	___display_name__ = "prompt"
	values = schema.List(cnt_interfaces.IinlineStatic , title="Choice interactions")

class IblockInteraction(cnt_interfaces.Iblock, cnt_interfaces.Iflow, Iinteraction):
	prompt = schema.Object(Iprompt, title='An optional prompt for the interaction', required=False)
	
class Ichoice(basic_interfaces.IbodyElement, attr_interfaces.IchoiceAttrGroup):
	pass

# simple interactions

class IassociableChoice(Ichoice, attr_interfaces.IassociableChoiceAttrGroup):
	pass

class IgapChoice(IassociableChoice, attr_interfaces.IgapChoiceAttrGroup):
	pass

class IgapText(IgapChoice, IFiniteSequence):
	___display_name__ = 'gapText'
	texrOrVariable = schema.List(basic_interfaces.ITextOrVariable, title="The variables", min_length=0)
	
class IgapImg(IgapChoice, attr_interfaces.IgapImgAttrGroup, IFiniteSequence):
	___display_name__ = 'gapImg'
	object = schema.Object(cnt_interfaces.Iobject, title="game images", required=True)
	
class Igap(IassociableChoice, cnt_interfaces.IinlineStatic, attr_interfaces.IgapAttrGroup):
	___display_name__ = 'gap'
	
class IsimpleAssociableChoice(IassociableChoice, attr_interfaces.IsimpleAssociableChoiceAttrGroup, IFiniteSequence):
	___display_name__ = 'simpleAssociableChoice'
	flowStatic = schema.List(cnt_interfaces.IflowStatic, title="associableChoice is a choice that contains flowStatic objects", min_length=0)

class IsimpleChoice(Ichoice, attr_interfaces.IsimpleChoiceAttrGroup):
	___display_name__ = "simpleChoice"
	flowStatic = schema.List(cnt_interfaces.IflowStatic, title="simpleChoice is a choice that contains flowStatic objects")
	
class IassociateInteraction(IblockInteraction, attr_interfaces.IassociateInteractionAttrGroup, IFiniteSequence):
	___display_name__ = "associateInteraction"
	simpleAssociableChoice = schema.List(IsimpleAssociableChoice , title="An ordered set of choices.", min_length=1)
	
class IchoiceInteraction(IblockInteraction, attr_interfaces.IchoiceInteractionAttrGroup, IFiniteSequence):
	___display_name__ = "choiceInteraction"
	simpleChoice = schema.List(IsimpleChoice , title="An ordered list of the choices that are displayed to the user",  min_length=1)

class IorderInteraction(IblockInteraction, attr_interfaces.IorderInteractionAttrGroup, IFiniteSequence):
	___display_name__ = "orderInteraction"
	simpleChoice = schema.List(IsimpleChoice , title="An ordered list of the choices that are displayed to the user",  min_length=1)

class IsimpleMatchSet(IFiniteSequence):
	___display_name__ = "simpleMatchSet"
	simpleAssociableChoice = schema.List(IsimpleAssociableChoice, title="An ordered set of choices for the set.", min_length=0)
	
class ImatchInteraction(IblockInteraction, attr_interfaces.ImatchInteractionAttrGroup, IFiniteSequence):
	___display_name__ = "matchInteraction"
	simpleMatchSet = schema.List(IsimpleMatchSet , title="The two sets of choices",  min_length=2, max_length=2)
	
class IgapMatchInteraction(IblockInteraction, attr_interfaces.IgapMatchInteractionAttrGroup):
	___display_name__ = "gapMatchInteraction"
	gapChoice = schema.List(IgapChoice, title="An ordered list of choices for filling the gaps",  min_length=1)
	blockStatic = schema.List(cnt_interfaces.IblockStatic, title="A piece of content that contains the gaps",  min_length=1)
	
# text-based interactions

class IinlineChoice(Ichoice, IFiniteSequence):
	___display_name__ = "inlineChoice"
	textOrVariable = schema.List(basic_interfaces.ITextOrVariable, title="Order list varibles", min_length=0)
	
class IinlineChoiceInteraction(IinlineInteraction, attr_interfaces.IinlineChoiceInteractionAttrGroup, IFiniteSequence):
	___display_name__ = "inlineChoiceInteraction"
	inlineChoice = schema.List(IinlineChoice , title="An ordered list of the choices that are displayed to the user",  min_length=0)
	
class IstringInteraction(attr_interfaces.IstringInteractionAttrGroup):
	pass

class ItextEntryInteraction(IinlineInteraction, IstringInteraction):
	__display_name__ = "textEntryInteraction"

class IextendedTextInteraction(IblockInteraction, IstringInteraction, attr_interfaces.IextendedTextInteractionAttrGroup):
	__display_name__ = "extendedTextInteraction"
	
class IhottextInteraction(IblockInteraction, attr_interfaces.IhottextInteractionAttrGroup, IFiniteSequence):
	__display_name__ = "hottextInteraction"
	blockStatic = schema.List(cnt_interfaces.IblockStatic, title="The ordered content of the interaction is simply a piece of content",  min_length=1)

class Ihottext(Ichoice, cnt_interfaces.IflowStatic, cnt_interfaces.IinlineStatic, IFiniteSequence):
	__display_name__ = "hottext"
	inlineStatic = schema.List(cnt_interfaces.IinlineStatic, title="The order content",  min_length=0)

# graphical interactions

class Ihotspot(attr_interfaces.IhotspotAttrGroup):
	pass

class IhotspotChoice(Ichoice, Ihotspot):
	__display_name__ = "hotspotChoice"

class IassociableHotspot(IassociableChoice, Ihotspot, attr_interfaces.IassociableHotspotAttrGroup):
	__display_name__ = "associableHotspot"
	
class IgraphicInteraction(IblockInteraction):
	object = schema.Object(cnt_interfaces.Iobject, title="The associated image", required=True)
	
class IhotspotInteraction(IgraphicInteraction, IFiniteSequence, attr_interfaces.IhotspotInteractiontAttrGroup):
	__display_name__ = "hotspotInteraction"
	hotspotChoice = schema.List(IhotspotChoice, title="The ordered choices",  min_length=1)
	
class IselectPointInteraction(IgraphicInteraction, attr_interfaces.IselectPointInteractionAttrGroup):
	__display_name__ = "selectPointInteraction"
	
class IgraphicOrderInteraction(IgraphicInteraction, IFiniteSequence, attr_interfaces.IgraphicOrderInteractiontAttrGroup):
	__display_name__ = "graphicOrderInteraction"
	hotspotChoice = schema.List(IhotspotChoice, title="The ordered choices",  min_length=1)
	
class IgraphicAssociateInteraction(IgraphicInteraction, IFiniteSequence, attr_interfaces.IgraphicAssociateInteractiontAttrGroup):
	__display_name__ = "graphicAssociateInteraction"
	associableHotspot = schema.List(IassociableHotspot , title="The ordered choices",  min_length=1)

class IgraphicGapMatchInteraction(IgraphicInteraction):
	__display_name__ = "graphicGapMatchInteraction"
	gapImg = schema.List(IgapImg, title="An ordered list of choices for filling the gaps",  min_length=1)
	associableHotspot  = schema.List(IassociableHotspot , title="The hotspots that define the gaps that are to be filled by the candidate",  min_length=1)

class IpositionObjectInteraction(Iinteraction, attr_interfaces.IpositionObjectInteractiontAttrGroup):
	__display_name__ = "positionObjectInteraction"
	object = schema.Object(cnt_interfaces.Iobject, title="The image to be positioned on the stage", required=True)
	
class IpositionObjectStage(cnt_interfaces.Iblock):
	__display_name__ = "positionObjectStage"
	object = schema.Object(cnt_interfaces.Iobject, title="The image to be used as a stage", required=True)
	positionObjectInteraction = schema.List(IpositionObjectInteraction, title="The ordered positionObjectInteraction",  min_length=1)
	
# miscellaneous interactions

class IsliderInteraction(IblockInteraction, attr_interfaces.IsliderInteractionAttrGroup):
	__display_name__ = "sliderInteraction"

class ImediaInteraction(IblockInteraction, attr_interfaces.ImediaInteractionAttrGroup):
	__display_name__ = "mediaInteraction"
	object = schema.Object(cnt_interfaces.Iobject, title="The media object itself", required=True)
		
class IdrawingInteraction(IblockInteraction):
	__display_name__ = "drawingInteraction"
	object = schema.Object(cnt_interfaces.Iobject, title="The image that acts as the canvas", required=True)
	
class IuploadInteraction(IblockInteraction, attr_interfaces.IuploadInteractionAttrGroup):
	__display_name__ = "uploadInteraction"
	
class IcustomInteraction(cnt_interfaces.Iblock, cnt_interfaces.Iflow, Iinteraction):
	__display_name__ = "customInteraction"
	
# alternative ways to provide hints and other supplementary material

class IinfoControl(cnt_interfaces.IblockStatic, basic_interfaces.IbodyElement, cnt_interfaces.IflowStatic):
	__display_name__ = "infoControl"
