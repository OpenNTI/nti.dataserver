from __future__ import unicode_literals, print_function

from zope import interface

from nti.assessment.qti.schema import (TextLineAttribute, BoolAttribute, IntAttribute)
	
class IFlowAttrGroup(interface.Interface):
	base = TextLineAttribute(title=u'The uri base', required=False, __name__='xml:base')

class IBodyElementAttrGroup(interface.Interface):
	id = TextLineAttribute(title=u'The element id', required=False)
	klass = TextLineAttribute(title=u'The class', required=False, __name__='class')
	lang = TextLineAttribute(title=u'The language code (RFC3066)', __name__='xml:lang', required=False, max_length=2, default='en')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	
class IPromptAttrGroup(IBodyElementAttrGroup):
	pass
	
class IChoiceAttrGroup(IBodyElementAttrGroup):
	identifier = TextLineAttribute(title=u'The element identifier', required=True)
	fixed = BoolAttribute(title=u'Fixed choice attribute', required=False)
	templateIdentifier = TextLineAttribute(title=u'The template identifier', required=False)
	showHide = BoolAttribute(title=u'Show hide flag', required=False)

class ISimpleChoiceAttrGroup(IChoiceAttrGroup):
	pass

class IInteractionAttrGroup(IBodyElementAttrGroup):
	responseIdentifier = TextLineAttribute(title=u'The response identifier', required=True)

class IBlockInteractionAttrGroup(IFlowAttrGroup, IInteractionAttrGroup):
	pass
	
class IChoiceInteractionAttrGroup(IFlowAttrGroup, IInteractionAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False)

class IAssessmentItemAttrGroup(interface.Interface):
	identifier = TextLineAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
