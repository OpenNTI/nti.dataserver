from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti.basic import interfaces as basic_interfaces
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

class IroundTo(Iexpression, attr_interfaces.IroundToAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IstatsOperator(Iexpression, attr_interfaces.IstatsOperatorAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)
	
class Imax(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)
	
class Imin(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)
	
class ImathOperator(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)

class Igcd(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)

class Ilcm(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)

class Irepeat(Iexpression, attr_interfaces.IrepeatAttrGroup, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)
	
class Imultiple(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=0, required=True)

class Iordered(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The ordered sub-expressions', min_length=0, required=True)
	
class IcontainerSize(Iexpression, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IisNull(Iexpression, attr_interfaces.IstatsOperatorAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Iindex(Iexpression, attr_interfaces.IindexAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IfieldValue(Iexpression, attr_interfaces.IfieldValueAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Irandom(Iexpression, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Imember(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Idelete(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Icontains(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Isubstring(Iexpression, attr_interfaces.IsubstringAttrGroup,  basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Inot(Iexpression, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The sub-expression", required=True)

class Iand(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Ior(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class IanyN(Iexpression, attr_interfaces.IanyNAttrGroup, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Imatch(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class IstringMatch(Iexpression, attr_interfaces.IstringMatchAttrGroup, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1,  max_length=2, title="The eval sub-expressions", required=True)

class IpatternMatch(Iexpression, attr_interfaces.IpatternMatchAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Iequal(Iexpression, attr_interfaces.IequalAttrGroup, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1,  max_length=2, title="The eval sub-expressions", required=True)

class IequalRounded(Iexpression, attr_interfaces.IequalRoundedAttrGroup, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1,  max_length=2, title="The eval sub-expressions", required=True)

class Iinside(Iexpression, attr_interfaces.IinsideAttrGroup, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expressions", required=True)

class Ilt(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Igt(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Ilte(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Igte(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class IdurationLT(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class IdurationGTE(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Isum(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Iproduct(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Isubtract(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)
	
class Idivide(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class Ipower(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class IintegerDivide(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class IintegerModulus(Iexpression, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class Itruncate(Iexpression, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Iround(Iexpression, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IintegerToFloat(Iexpression, basic_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IcustomOperator(Iexpression, attr_interfaces.IcustomOperatorAttrGroup, basic_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=0, max_length=2, title="The ordered eval sub-expressions", required=True)
