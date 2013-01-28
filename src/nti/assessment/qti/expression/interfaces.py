from __future__ import unicode_literals, print_function

from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class Iexpression(interface.Interface):
	pass
	
class IbaseValue(Iexpression, attr_interfaces.IbaseValueAttrGroup, basic_interfaces.IConcrete):
	pass

class Ivariable(Iexpression, attr_interfaces.IvariableAttrGroup, basic_interfaces.IConcrete):
	pass

class Idefault(Iexpression, attr_interfaces.IdefaultAttrGroup, basic_interfaces.IConcrete):
	pass

class Icorrect(Iexpression, attr_interfaces.IcorrectAttrGroup, basic_interfaces.IConcrete):
	pass

class ImapResponse(Iexpression, attr_interfaces.ImapResponseAttrGroup, basic_interfaces.IConcrete):
	pass

class ImapResponsePoint(Iexpression, attr_interfaces.ImapResponsePointAttrGroup, basic_interfaces.IConcrete):
	pass

class ImathConstant(Iexpression, attr_interfaces.ImathConstantAttrGroup, basic_interfaces.IConcrete):
	pass

class Inull(Iexpression, basic_interfaces.IConcrete):
	pass

class IrandomInteger(Iexpression, attr_interfaces.IrandomIntegerAttrGroup, basic_interfaces.IConcrete):
	pass
	
class IrandomFloat(Iexpression, attr_interfaces.IrandomFloatAttrGroup, basic_interfaces.IConcrete):
	pass

# expressions used only in outcomes processing

class IitemSubset(attr_interfaces.IitemSubsetAttrGroup):
	pass

class ItestVariables(Iexpression, attr_interfaces.ItestVariablesAttrGroup, basic_interfaces.IConcrete):
	pass

class IoutcomeMaximum(Iexpression, attr_interfaces.IoutcomeMaximumAttrGroup, basic_interfaces.IConcrete):
	pass

class IoutcomeMinimum(Iexpression, attr_interfaces.IoutcomeMinimumAttrGroup, basic_interfaces.IConcrete):
	pass

class InumberCorrect(Iexpression, basic_interfaces.IConcrete):
	pass

class InumberIncorrect(Iexpression, basic_interfaces.IConcrete):
	pass

class InumberResponded(Iexpression, basic_interfaces.IConcrete):
	pass

class InumberPresented(Iexpression, basic_interfaces.IConcrete):
	pass

class InumberSelected(Iexpression, basic_interfaces.IConcrete):
	pass

# operators



