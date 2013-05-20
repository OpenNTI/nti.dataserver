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
from . import interfaces as cnt_interfaces

@qti_creator
@interface.implementer(cnt_interfaces.ItextRun)
class TextRun(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iabbr)
class Abbr(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iacronym)
class Acronym(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iaddress)
class Address(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iblockquote)
class Blockquote(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ibr)
class Br(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Icite)
class Cite(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Icode)
class Code(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Idfn)
class Dfn(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Idiv)
class Div(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iem)
class Em(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Ih1)
class H1(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ih2)
class H2(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ih3)
class H3(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ih4)
class H4(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ih5)
class H5(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ih6)
class H6(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ikbd)
class Kbd(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ip)
class P(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ipre)
class Pre(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Iq)
class Q(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Isamp)
class Samp(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ispan)
class Span(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Istrong)
class Strong(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ivar)
class Var(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Idl)
class Dl(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Idt)
class Dt(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Idd)
class Dd(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ili)
class Li(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iol)
class Ol(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Iul)
class Ul(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iobject)
class Object(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Iparam)
class Param(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ib)
class B(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ibig)
class Big(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ihr)
class Hr(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ii)
class I(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ismall)
class Small(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Isub)
class Sub(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Isup)
class Sup(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Itt)
class Tt(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Icaption)
class Caption(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Icol)
class Col(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Icolgroup)
class Colgroup(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Itd)
class Td(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ith)
class Th(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Itr)
class Tr(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Ithead)
class Thead(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Itfoot)
class Tfoot(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Itbody)
class Tbody(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Itable)
class Table(QTIElement):
	pass
	
@qti_creator
@interface.implementer(cnt_interfaces.Iimg)
class Img(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Ia)
class A(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Imath)
class Math(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.IfeedbackBlock)
class FeedbackBlock(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.IfeedbackInline)
class FeedbackInline(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.IrubricBlock)
class RubricBlock(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.Istylesheet)
class Stylesheet(QTIElement):
	pass

@qti_creator
@interface.implementer(cnt_interfaces.IitemBody)
class ItemBody(QTIElement):
	pass
