# -*- coding: utf-8 -*-
"""
Defines QTI expression interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema

from .. import interfaces as qti_interfaces
from ..attributes import interfaces as attr_interfaces

class Iexpression(qti_interfaces.IQTIElement):
	pass
	
class IbaseValue(Iexpression, attr_interfaces.IbaseValueAttrGroup, qti_interfaces.IConcrete):
	pass

class Ivariable(Iexpression, attr_interfaces.IvariableAttrGroup, qti_interfaces.IConcrete):
	pass

class Idefault(Iexpression, attr_interfaces.IdefaultAttrGroup, qti_interfaces.IConcrete):
	pass

class Icorrect(Iexpression, attr_interfaces.IcorrectAttrGroup, qti_interfaces.IConcrete):
	pass

class ImapResponse(Iexpression, attr_interfaces.ImapResponseAttrGroup, qti_interfaces.IConcrete):
	pass

class ImapResponsePoint(Iexpression, attr_interfaces.ImapResponsePointAttrGroup, qti_interfaces.IConcrete):
	pass

class ImathConstant(Iexpression, attr_interfaces.ImathConstantAttrGroup, qti_interfaces.IConcrete):
	pass

class Inull(Iexpression, qti_interfaces.IConcrete):
	pass

class IrandomInteger(Iexpression, attr_interfaces.IrandomIntegerAttrGroup, qti_interfaces.IConcrete):
	pass
	
class IrandomFloat(Iexpression, attr_interfaces.IrandomFloatAttrGroup, qti_interfaces.IConcrete):
	pass

# expressions used only in outcomes processing

class IitemSubset(attr_interfaces.IitemSubsetAttrGroup):
	pass

class ItestVariables(Iexpression, attr_interfaces.ItestVariablesAttrGroup, qti_interfaces.IConcrete):
	pass

class IoutcomeMaximum(Iexpression, attr_interfaces.IoutcomeMaximumAttrGroup, qti_interfaces.IConcrete):
	pass

class IoutcomeMinimum(Iexpression, attr_interfaces.IoutcomeMinimumAttrGroup, qti_interfaces.IConcrete):
	pass

class InumberCorrect(Iexpression, qti_interfaces.IConcrete):
	pass

class InumberIncorrect(Iexpression, qti_interfaces.IConcrete):
	pass

class InumberResponded(Iexpression, qti_interfaces.IConcrete):
	pass

class InumberPresented(Iexpression, qti_interfaces.IConcrete):
	pass

class InumberSelected(Iexpression, qti_interfaces.IConcrete):
	pass

# operators

class IroundTo(Iexpression, attr_interfaces.IroundToAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IstatsOperator(Iexpression, attr_interfaces.IstatsOperatorAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)
	
class Imax(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)
	
class Imin(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)
	
class ImathOperator(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)

class Igcd(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)

class Ilcm(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)

class Irepeat(Iexpression, attr_interfaces.IrepeatAttrGroup, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=1, required=True)
	
class Imultiple(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The sub-expressions', min_length=0, required=True)

class Iordered(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), title='The ordered sub-expressions', min_length=0, required=True)
	
class IcontainerSize(Iexpression, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IisNull(Iexpression, attr_interfaces.IstatsOperatorAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Iindex(Iexpression, attr_interfaces.IindexAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IfieldValue(Iexpression, attr_interfaces.IfieldValueAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Irandom(Iexpression, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Imember(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Idelete(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Icontains(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Isubstring(Iexpression, attr_interfaces.IsubstringAttrGroup,  qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class Inot(Iexpression, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The sub-expression", required=True)

class Iand(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Ior(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class IanyN(Iexpression, attr_interfaces.IanyNAttrGroup, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Imatch(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=2, max_length=2, title="The ordered eval sub-expressions", required=True)

class IstringMatch(Iexpression, attr_interfaces.IstringMatchAttrGroup, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1,  max_length=2, title="The eval sub-expressions", required=True)

class IpatternMatch(Iexpression, attr_interfaces.IpatternMatchAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Iequal(Iexpression, attr_interfaces.IequalAttrGroup, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1,  max_length=2, title="The eval sub-expressions", required=True)

class IequalRounded(Iexpression, attr_interfaces.IequalRoundedAttrGroup, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1,  max_length=2, title="The eval sub-expressions", required=True)

class Iinside(Iexpression, attr_interfaces.IinsideAttrGroup, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expressions", required=True)

class Ilt(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Igt(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Ilte(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Igte(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class IdurationLT(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class IdurationGTE(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The eval sub-expressions", required=True)

class Isum(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Iproduct(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, title="The eval sub-expressions", required=True)

class Isubtract(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)
	
class Idivide(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class Ipower(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class IintegerDivide(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class IintegerModulus(Iexpression, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=1, max_length=2, title="The ordered eval sub-expressions", required=True)

class Itruncate(Iexpression, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class Iround(Iexpression, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IintegerToFloat(Iexpression, qti_interfaces.IConcrete):
	expression = schema.Object(Iexpression, title="The eval sub-expression", required=True)

class IcustomOperator(Iexpression, attr_interfaces.IcustomOperatorAttrGroup, qti_interfaces.IConcrete):
	expression = schema.List(schema.Object(Iexpression), min_length=0, max_length=2, title="The ordered eval sub-expressions", required=True)
