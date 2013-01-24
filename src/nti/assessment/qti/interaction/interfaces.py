from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.attributes import interfaces as atr_interfaces

class IChoiceContent(interface.Interface):
	pass

class IPrompt(IChoiceContent):
	__display_name__ = "prompt"
	
class ISimpleChoice(IChoiceContent, atr_interfaces.ISimpleChoiceAttrGroup):
	__display_name__ = "simpleChoice"
	
class IChoice(atr_interfaces.IChoiceInteractionAttrGroup, IFiniteSequence):
	__display_name__ = "choice"
	interactions = schema.List(IChoiceContent, title="Choice interactions")