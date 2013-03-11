# -*- coding: utf-8 -*-
"""
Defines QTI outcome elements

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..basic.elements import QTIElement
from ..basic.elements import qti_creator
from . import interfaces as exp_interfaces

@qti_creator
@interface.implementer(exp_interfaces.IbaseValue)
class BaseValue(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Ivariable)
class Variable(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Idefault)
class Default(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Icorrect)
class Correct(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.ImapResponse)
class MapResponse(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.ImapResponsePoint)
class MapResponsePoint(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.ImathConstant)
class MathConstant(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Inull)
class Null(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IrandomInteger)
class RandomInteger(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IrandomFloat)
class RandomFloat(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.ItestVariables)
class TestVariables(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IoutcomeMaximum)
class OutcomeMaximum(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IoutcomeMinimum)
class OutcomeMinimum(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.InumberCorrect)
class NumberCorrect(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.InumberIncorrect)
class NumberIncorrect(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.InumberResponded)
class NumberResponded(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.InumberPresented)
class NumberPresented(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.InumberSelected)
class NumberSelected(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IroundTo)
class RoundTo(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IstatsOperator)
class StatsOperator(QTIElement):
	pass
	
@qti_creator
@interface.implementer(exp_interfaces.Imax)
class Max(QTIElement):
	pass
	
@qti_creator
@interface.implementer(exp_interfaces.Imin)
class Min(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.ImathOperator)
class MathOperator(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Igcd)
class Gcd(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Ilcm)
class Lcm(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Irepeat)
class Repeat(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Imultiple)
class Multiple(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Iordered)
class Ordered(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IcontainerSize)
class ContainerSize(QTIElement):
	pass
	
@qti_creator
@interface.implementer(exp_interfaces.IisNull)
class IsNull(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Iindex)
class Index(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IfieldValue)
class FieldValue(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Irandom)
class Random(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Imember)
class Member(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Idelete)
class Delete(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Icontains)
class Contains(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Isubstring)
class Substring(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Inot)
class Not(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Iand)
class And(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Ior)
class Or(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IanyN)
class AnyN(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Imatch)
class Match(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IstringMatch)
class StringMatch(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IpatternMatch)
class PatternMatch(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Iequal)
class Equal(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IequalRounded)
class EqualRounded(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Iinside)
class Inside(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Ilt)
class Lt(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Igt)
class Gt(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Ilte)
class Lte(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Igte)
class Gte(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IdurationLT)
class DurationLT(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IdurationGTE)
class DurationGTE(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Isum)
class Sum(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Iproduct)
class Product(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Isubtract)
class Subtract(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Idivide)
class Divide(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Ipower)
class Power(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IintegerDivide)
class IntegerDivide(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.IintegerModulus)
class IntegerModulus(QTIElement):
	pass

@qti_creator
@interface.implementer(exp_interfaces.Itruncate)
class Truncate(QTIElement):
	pass

@interface.implementer(exp_interfaces.Iround)
class Round(QTIElement):
	pass

@interface.implementer(exp_interfaces.IintegerToFloat)
class IntegerToFloat(QTIElement):
	pass

@interface.implementer(exp_interfaces.IcustomOperator)
class CustomOperator(QTIElement):
	pass
