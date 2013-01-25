from __future__ import unicode_literals, print_function

from zope import schema
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class IInteraction(qti_interfaces.IBodyElement, attr_interfaces.IInteractionAttrGroup):
	pass

class IInlineInteraction(cnt_interfaces.IFlow, cnt_interfaces.IInline, IInteraction):
	pass

class IEndAttemptInteraction(IInlineInteraction, attr_interfaces.IEndAttemptInteractionAttrGroup):
	__display_name__ = "endAttemptInteraction"
		
class IPrompt(qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "prompt"
	values = schema.List(cnt_interfaces.IInlineStatic , title="Choice interactions")

#TODO:  drawingInteraction,  graphicInteraction,  mediaInteraction, sliderInteraction, uploadInteraction
class IBlockInteraction(cnt_interfaces.IBlock, cnt_interfaces.IFlow, IInteraction):
	prompt = schema.Object(IPrompt, title='An optional prompt for the interaction', required=False)
	
class IChoice(qti_interfaces.IBodyElement, attr_interfaces.IChoiceAttrGroup):
	pass

# simple interactions

#TODO: associableHotspot	
class IAssociableChoice(IChoice, attr_interfaces.IAssociableChoiceAttrGroup):
	pass

class IGapChoice(IAssociableChoice, attr_interfaces.IGapChoiceAttrGroup):
	pass

class IGapText(IGapChoice, IFiniteSequence):
	__display_name__ = 'gapText'
	values = schema.List(qti_interfaces.ITextOrVariable, title="The variables", min_length=0)
	
class IGapImg(IGapChoice, attr_interfaces.IGapImgAttrGroup, IFiniteSequence):
	__display_name__ = 'gapImg'
	values = schema.List(cnt_interfaces.IObject, title="game images", min_length=1, max_length=1)
	
class IGap(IAssociableChoice, cnt_interfaces.IInlineStatic, attr_interfaces.IGapAttrGroup):
	__display_name__ = 'gap'
	
class ISimpleAssociableChoice(IAssociableChoice, attr_interfaces.ISimpleAssociableChoiceAttrGroup, IFiniteSequence):
	__display_name__ = 'simpleAssociableChoice'
	values = schema.List(cnt_interfaces.IFlowStatic, title="associableChoice is a choice that contains flowStatic objects", min_length=0)
	
#TODO: hotspotChoice, hottext, inlineChoice, 
class ISimpleChoice(IChoice, attr_interfaces.ISimpleChoiceAttrGroup):
	__display_name__ = "simpleChoice"
	values = schema.List(cnt_interfaces.IFlowStatic, title="simpleChoice is a choice that contains flowStatic objects")
	
class IAssociateInteraction(IBlockInteraction, attr_interfaces.IAssociateInteractionAttrGroup, IFiniteSequence):
	__display_name__ = "associateInteraction"
	values = schema.List(ISimpleAssociableChoice , title="An ordered set of choices.", min_length=1)
	
class IChoiceInteraction(IBlockInteraction, attr_interfaces.IChoiceInteractionAttrGroup, IFiniteSequence):
	__display_name__ = "choiceInteraction"
	values = schema.List(ISimpleChoice , title="An ordered list of the choices that are displayed to the user",  min_length=1)

class IOrderInteraction(IBlockInteraction, attr_interfaces.IOrderInteractionAttrGroup, IFiniteSequence):
	__display_name__ = "orderInteraction"
	values = schema.List(ISimpleChoice , title="An ordered list of the choices that are displayed to the user",  min_length=1)

class ISimpleMatchSet(IFiniteSequence):
	__display_name__ = "simpleMatchSet"
	values = schema.List(ISimpleAssociableChoice, title="An ordered set of choices for the set.", min_length=0)
	
class IMatchInteraction(IBlockInteraction, attr_interfaces.IMatchInteractioAttrGroup, IFiniteSequence):
	__display_name__ = "matchInteraction"
	values = schema.List(ISimpleMatchSet , title="The two sets of choices",  min_length=2, max_length=2)
	
class IGapMatchInteraction(IBlockInteraction, attr_interfaces.IGapMatchInteractioAttrGroup):
	__display_name__ = "gapMatchInteraction"
	gapChoice = schema.List(IGapChoice, title="An ordered list of choices for filling the gaps",  min_length=1)
	blockStatic  = schema.List(cnt_interfaces.IBlockStatic, title="A piece of content that contains the gaps",  min_length=1)
	
# text-based interactions

class IInlineChoice(IChoice):
	__display_name__ = "inlineChoice"

class IInlineChoiceInteraction(IInlineInteraction, attr_interfaces.IInlineChoiceInteractionAttrGroup, IFiniteSequence):
	__display_name__ = "inlineChoiceInteraction"
	values = schema.List(IInlineChoice , title="An ordered list of the choices that are displayed to the user",  min_length=0)
	
class IStringInteraction(attr_interfaces.IStringInteractionAttrGroup):
	pass

class ITextEntryInteraction(IInlineInteraction, IStringInteraction):
	_display_name__ = "textEntryInteraction"

class IExtendedTextInteractionInteraction(IBlockInteraction, IStringInteraction, attr_interfaces.IExtendedTextInteractionAttrGroup):
	_display_name__ = "extendedTextInteraction"
	
class IHottextInteraction(IBlockInteraction, attr_interfaces.IBlockInteractionAttrGroup, IFiniteSequence):
	_display_name__ = "hottextInteraction"
	values = schema.List(cnt_interfaces.IBlockStatic, title="The content of the interaction is simply a piece of content",  min_length=1)

class IHottext(IChoice, cnt_interfaces.IFlowStatic, cnt_interfaces.IInlineStatic, IFiniteSequence):
	_display_name__ = "hottext"
	values = schema.List(cnt_interfaces.IInlineStatic, title="The content",  min_length=0)

# graphical interactions

class IHotspot(attr_interfaces.IHotspotAttrGroup):
	pass

class IHotspotChoice(IChoice, IHotspot):
	_display_name__ = "hotspotChoice"

class IAssociableHotspot(IAssociableChoice, IHotspot, attr_interfaces.IAssociableHotspotAttrGroup):
	_display_name__ = "associableHotspot"
	
class IGraphicInteraction(IBlockInteraction):
	object = schema.List(cnt_interfaces.IObject, title="The associated image",  min_length=1, max_length=1)
	
class IHotspotInteraction(IGraphicInteraction, IFiniteSequence, attr_interfaces.IAssociableHotspotAttrGroup):
	_display_name__ = "hotspotInteraction"
	values = schema.List(IHotspotChoice, title="The ordered choices",  min_length=1)
	