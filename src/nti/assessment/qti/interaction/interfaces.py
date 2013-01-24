from __future__ import unicode_literals, print_function

from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.schema import (TextLineAttribute, BoolAttribute, IntAttribute)
	
class IInteractionAttrGroup(qti_interfaces.IBodyElementAttrGroup):
	responseIdentifier = TextLineAttribute(title=u'The response identifier', required=True)

class IBlockInteractionAttrGroup(qti_interfaces.IFlowAttrGroup, IInteractionAttrGroup):
	pass
	
class IChoiceInteractionAttrGroup(qti_interfaces.IFlowAttrGroup, IInteractionAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False)
