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

class IendAttemptInteraction(IinlineInteraction, attr_interfaces.IendAttemptInteractionAttrGroup, basic_interfaces.IConcrete):
	pass
		
class Iprompt(basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	values = schema.List(schema.Object(cnt_interfaces.IinlineStatic) , title="Choice interactions")

class IblockInteraction(cnt_interfaces.Iblock, cnt_interfaces.Iflow, Iinteraction):
	prompt = schema.Object(Iprompt, title='An optional prompt for the interaction', required=False)
	
class Ichoice(basic_interfaces.IbodyElement, attr_interfaces.IchoiceAttrGroup):
	pass

# simple interactions

class IassociableChoice(Ichoice, attr_interfaces.IassociableChoiceAttrGroup):
	pass

class IgapChoice(IassociableChoice, attr_interfaces.IgapChoiceAttrGroup):
	pass

class IgapText(IgapChoice, IFiniteSequence, basic_interfaces.IConcrete):
	texrOrVariable = schema.List(schema.Object(basic_interfaces.ITextOrVariable), title="The variables", min_length=0)
	
class IgapImg(IgapChoice, attr_interfaces.IgapImgAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	object = schema.Object(cnt_interfaces.Iobject, title="game images", required=True)
	
class Igap(IassociableChoice, cnt_interfaces.IinlineStatic, attr_interfaces.IgapAttrGroup, basic_interfaces.IConcrete):
	pass
	
class IsimpleAssociableChoice(IassociableChoice, attr_interfaces.IsimpleAssociableChoiceAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	flowStatic = schema.List(schema.Object(cnt_interfaces.IflowStatic), title="associableChoice is a choice that contains flowStatic objects", min_length=0)

class IsimpleChoice(Ichoice, attr_interfaces.IsimpleChoiceAttrGroup, basic_interfaces.IConcrete):
	flowStatic = schema.List(schema.Object(cnt_interfaces.IflowStatic), title="simpleChoice is a choice that contains flowStatic objects")
	
class IassociateInteraction(IblockInteraction, attr_interfaces.IassociateInteractionAttrGroup, IFiniteSequence,
							basic_interfaces.IConcrete):
	simpleAssociableChoice = schema.List(schema.Object(IsimpleAssociableChoice), title="An ordered set of choices.", min_length=1)
	
class IchoiceInteraction(IblockInteraction, attr_interfaces.IchoiceInteractionAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	simpleChoice = schema.List(schema.Object(IsimpleChoice), title="An ordered list of the choices that are displayed to the user",  min_length=1)

class IorderInteraction(IblockInteraction, attr_interfaces.IorderInteractionAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	simpleChoice = schema.List(schema.Object(IsimpleChoice), title="An ordered list of the choices that are displayed to the user",  min_length=1)

class IsimpleMatchSet(IFiniteSequence, basic_interfaces.IConcrete):
	simpleAssociableChoice = schema.List(schema.Object(IsimpleAssociableChoice), title="An ordered set of choices for the set.", min_length=0)
	
class ImatchInteraction(IblockInteraction, attr_interfaces.ImatchInteractionAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	simpleMatchSet = schema.List(schema.Object(IsimpleMatchSet), title="The two sets of choices",  min_length=2, max_length=2)
	
class IgapMatchInteraction(IblockInteraction, attr_interfaces.IgapMatchInteractionAttrGroup, basic_interfaces.IConcrete):
	gapChoice = schema.List(schema.Object(IgapChoice), title="An ordered list of choices for filling the gaps",  min_length=1)
	blockStatic = schema.List(schema.Object(cnt_interfaces.IblockStatic), title="A piece of content that contains the gaps",  min_length=1)
	
# text-based interactions

class IinlineChoice(Ichoice, IFiniteSequence, basic_interfaces.IConcrete):
	textOrVariable = schema.List(schema.Object(basic_interfaces.ITextOrVariable), title="Order list varibles", min_length=0)
	
class IinlineChoiceInteraction(IinlineInteraction, attr_interfaces.IinlineChoiceInteractionAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	inlineChoice = schema.List(schema.Object(IinlineChoice), title="An ordered list of the choices that are displayed to the user",  min_length=0)
	
class IstringInteraction(attr_interfaces.IstringInteractionAttrGroup):
	pass

class ItextEntryInteraction(IinlineInteraction, IstringInteraction, basic_interfaces.IConcrete):
	pass

class IextendedTextInteraction(IblockInteraction, IstringInteraction, attr_interfaces.IextendedTextInteractionAttrGroup,basic_interfaces.IConcrete):
	pass
	
class IhottextInteraction(IblockInteraction, attr_interfaces.IhottextInteractionAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	blockStatic = schema.List(schema.Object(cnt_interfaces.IblockStatic), title="The ordered content of the interaction is simply a piece of content",  min_length=1)

class Ihottext(Ichoice, cnt_interfaces.IflowStatic, cnt_interfaces.IinlineStatic, IFiniteSequence, basic_interfaces.IConcrete):
	inlineStatic = schema.List(schema.Object(cnt_interfaces.IinlineStatic), title="The order content",  min_length=0)

# graphical interactions

class Ihotspot(attr_interfaces.IhotspotAttrGroup):
	pass

class IhotspotChoice(Ichoice, Ihotspot, basic_interfaces.IConcrete):
	pass

class IassociableHotspot(IassociableChoice, Ihotspot, attr_interfaces.IassociableHotspotAttrGroup, basic_interfaces.IConcrete):
	pass
	
class IgraphicInteraction(IblockInteraction):
	object = schema.Object(cnt_interfaces.Iobject, title="The associated image", required=True)
	
class IhotspotInteraction(IgraphicInteraction, IFiniteSequence, attr_interfaces.IhotspotInteractiontAttrGroup, basic_interfaces.IConcrete):
	hotspotChoice = schema.List(schema.Object(IhotspotChoice), title="The ordered choices",  min_length=1)
	
class IselectPointInteraction(IgraphicInteraction, attr_interfaces.IselectPointInteractionAttrGroup, basic_interfaces.IConcrete):
	pass
	
class IgraphicOrderInteraction(IgraphicInteraction, IFiniteSequence, attr_interfaces.IgraphicOrderInteractiontAttrGroup, basic_interfaces.IConcrete):
	hotspotChoice = schema.List(schema.Object(IhotspotChoice), title="The ordered choices",  min_length=1)
	
class IgraphicAssociateInteraction(IgraphicInteraction, IFiniteSequence, attr_interfaces.IgraphicAssociateInteractiontAttrGroup, basic_interfaces.IConcrete):
	associableHotspot = schema.List(schema.Object(IassociableHotspot), title="The ordered choices",  min_length=1)

class IgraphicGapMatchInteraction(IgraphicInteraction, basic_interfaces.IConcrete):
	gapImg = schema.List(schema.Object(IgapImg), title="An ordered list of choices for filling the gaps",  min_length=1)
	associableHotspot  = schema.List(schema.Object(IassociableHotspot), title="The hotspots that define the gaps that are to be filled by the candidate",  min_length=1)

class IpositionObjectInteraction(Iinteraction, attr_interfaces.IpositionObjectInteractiontAttrGroup, basic_interfaces.IConcrete):
	object = schema.Object(cnt_interfaces.Iobject, title="The image to be positioned on the stage", required=True)
	
class IpositionObjectStage(cnt_interfaces.Iblock, basic_interfaces.IConcrete):
	object = schema.Object(cnt_interfaces.Iobject, title="The image to be used as a stage", required=True)
	positionObjectInteraction = schema.List(schema.Object(IpositionObjectInteraction), title="The ordered positionObjectInteraction",  min_length=1)
	
# miscellaneous interactions

class IsliderInteraction(IblockInteraction, attr_interfaces.IsliderInteractionAttrGroup, basic_interfaces.IConcrete):
	pass

class ImediaInteraction(IblockInteraction, attr_interfaces.ImediaInteractionAttrGroup, basic_interfaces.IConcrete):
	object = schema.Object(cnt_interfaces.Iobject, title="The media object itself", required=True)
		
class IdrawingInteraction(IblockInteraction, basic_interfaces.IConcrete):
	object = schema.Object(cnt_interfaces.Iobject, title="The image that acts as the canvas", required=True)
	
class IuploadInteraction(IblockInteraction, attr_interfaces.IuploadInteractionAttrGroup, basic_interfaces.IConcrete):
	pass
	
class IcustomInteraction(cnt_interfaces.Iblock, cnt_interfaces.Iflow, Iinteraction, basic_interfaces.IConcrete):
	pass
	
# alternative ways to provide hints and other supplementary material

class IinfoControl(cnt_interfaces.IblockStatic, basic_interfaces.IbodyElement, cnt_interfaces.IflowStatic, basic_interfaces.IConcrete):
	pass
