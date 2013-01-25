from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces
	
class IobjectFlow(interface.Interface):
	pass

class Iinline(interface.Interface):
	pass
			
class Iblock(interface.Interface):
	pass
	
class Iflow(IobjectFlow, attr_interfaces.IflowAttrGroup):
	pass
	
class IinlineStatic(Iinline):
	pass
	
class IblockStatic(Iblock):
	pass
	
class IflowStatic(Iflow):
	pass
	
class IsimpleInline(qti_interfaces.IbodyElement, IflowStatic, IinlineStatic, IFiniteSequence):
	inline = schema.List(Iinline, 'inline objects contained', min_length=0)
	
class IsimpleBlock(IflowStatic, qti_interfaces.IbodyElement, IblockStatic, IFiniteSequence):
	block = schema.List(Iblock, 'block objects contained', min_length=0)
	
class IatomicInline(IflowStatic, qti_interfaces.IbodyElement, IinlineStatic):
	pass
	
class IAtomicBlock(qti_interfaces.IbodyElement, IflowStatic, IblockStatic, IFiniteSequence):
	inline = schema.List(Iinline, 'The ordered inline objects contained', min_length=0)

class ITextRun(IflowStatic, IinlineStatic, qti_interfaces.ITextOrVariable):
	__display_name__ = "textRun"
	
# xhtml elements

class Iabbr(IsimpleInline):
	__display_name__ = "abbr"
	
class Iacronym(IsimpleInline):
	__display_name__ = "acronym"
	
class Iaddress(IAtomicBlock):
	__display_name__ = "address"

class Iblockquote(IsimpleBlock, attr_interfaces.IblockquoteAttrGroup):
	__display_name__ = "blockquote"
	
class Ibr(IatomicInline):
	__display_name__ = "br"
	
class Icite(IsimpleInline):
	__display_name__ = "cite"
	
class Icode(IsimpleInline):
	__display_name__ = "code"
	
class Idfn(IsimpleInline):
	__display_name__ = "dfn"
	
class Idiv(IflowStatic, qti_interfaces.IbodyElement, IblockStatic, IFiniteSequence):
	__display_name__ = "div"
	flow = schema.List(Iflow, 'flow objects contained', min_length=0)
	
class Iem(IsimpleInline):
	__display_name__ = "em"
	
class Ih1(IAtomicBlock):
	__display_name__ = "h1"

class Ih2(IAtomicBlock):
	__display_name__ = "h2"

class Ih3(IAtomicBlock):
	__display_name__ = "h3"		
	
class Ih4(IAtomicBlock):
	__display_name__ = "h4"
	
class Ih5(IAtomicBlock):
	__display_name__ = "h5"
	
class Ih6(IAtomicBlock):
	__display_name__ = "h6"
	
class Ikbd(IsimpleInline):
	__display_name__ = "kbd"
	
class Ip(IAtomicBlock):
	__display_name__ = "p"
	
class Ipre(IAtomicBlock):
	"""
	Although pre inherits from atomicBlock it must not contain, either directly or indirectly,
	any of the following objects: img, object, big, small, sub, sup.
	"""
	__display_name__ = "pre"
	
class Iq(IsimpleInline, attr_interfaces.IqAttrGroup):
	__display_name__ = "q"
	
class Isamp(IsimpleInline):
	__display_name__ = "samp"
	
class Ispan(IsimpleInline):
	__display_name__ = "span"

class Istrong(IsimpleInline):
	__display_name__ = "strong"
	
class Ivar(IsimpleInline):
	__display_name__ = "var"

# list elements

class IDLElement(qti_interfaces.IbodyElement):
	pass

class Idl(IblockStatic, qti_interfaces.IbodyElement, IflowStatic, IFiniteSequence):
	__display_name__ = "dl"
	dlElement = schema.List(IDLElement, 'The ordered dl elements contained', min_length=0)
	
class Idt(IDLElement, IFiniteSequence):
	__display_name__ = "dt"
	inline = schema.List(Iinline, 'The ordered inline elements contained', min_length=0)

class Idd(IDLElement, IFiniteSequence):
	__display_name__ = "dd"
	flow = schema.List(Iflow, 'The ordered flow elements contained', min_length=0)

class Ili(qti_interfaces.IbodyElement, IFiniteSequence):
	__display_name__ = "li"
	flow = schema.List(Iflow, 'The ordered flow elements contained', min_length=0)

class Iol(IblockStatic, qti_interfaces.IbodyElement, IflowStatic, IFiniteSequence):
	__display_name__ = "ol"
	li = schema.List(Ili, 'The ordered li elements contained', min_length=0)
	
class Iul(IblockStatic, qti_interfaces.IbodyElement, IflowStatic, IFiniteSequence):
	__display_name__ = "ul"
	li = schema.List(Ili, 'The ordered li elements contained', min_length=0)
		
# object elements

class Iobject(qti_interfaces.IbodyElement, IflowStatic, IinlineStatic, IFiniteSequence, attr_interfaces.IobjectAttrGroup):
	__display_name__ = "object"
	objectFlow = schema.List(IobjectFlow, 'The ordered objectflow elements contained', min_length=0)

class Iparam(IobjectFlow, attr_interfaces.IparamAttrGroup):
	__display_name__ = "param"
	
# presentation Elements

class Ib(IsimpleInline):
	__display_name__ = "b"

class Ibig(IsimpleInline):
	__display_name__ = "big"	

class Ihr(IblockStatic, qti_interfaces.IbodyElement, IflowStatic):
	__display_name__ = "hr"	

class Ii(IsimpleInline):
	__display_name__ = "i"	

class Ismall(IsimpleInline):
	__display_name__ = "small"	

class Isub(IsimpleInline):
	__display_name__ = "sub"	

class Isup(IsimpleInline):
	__display_name__ = "sup"	

class Itt(IsimpleInline):
	__display_name__ = "tt"	

# table elements

class Icaption(qti_interfaces.IbodyElement, IFiniteSequence):
	__display_name__ = "caption"	
	inline = schema.List(Iinline, 'The ordered inline elements contained', min_length=0)

class Icol(qti_interfaces.IbodyElement, attr_interfaces.IcolAttrGroup):
	__display_name__ = "col"	
	
class Icolgroup(qti_interfaces.IbodyElement, attr_interfaces.IcolgroupAttrGroup, IFiniteSequence):
	__display_name__ = "colgroup"	
	col = schema.List(Icol, 'The ordered col elements contained', min_length=0)

class ItableCell(qti_interfaces.IbodyElement, attr_interfaces.ItableCellAttrGroup, IFiniteSequence):
	flow = schema.List(Iflow, 'The ordered flow elements contained', min_length=0)

class Itd(ItableCell):
	__display_name__ = "td"	
	
class Ith(ItableCell):
	__display_name__ = "th"	
	
class Itr( qti_interfaces.IbodyElement, IFiniteSequence):
	__display_name__ = "tr"
	tableCell = schema.List(ItableCell, 'tableCell elements contained', min_length=0)
	
class Ithead( qti_interfaces.IbodyElement, IFiniteSequence):
	__display_name__ = "thead"
	tr = schema.List(Itr, 'The ordered tr elements contained', min_length=1)
	
class Itfoot( qti_interfaces.IbodyElement, IFiniteSequence):
	__display_name__ = "tfoot"
	tr = schema.List(Itr, 'The ordered tr elements contained', min_length=1)
	
class Itbody( qti_interfaces.IbodyElement, IFiniteSequence):
	__display_name__ = "tbody"
	tr = schema.List(Itr, 'The ordered tr elements contained', min_length=1)
	
class Itable(IblockStatic, qti_interfaces.IbodyElement, IflowStatic, attr_interfaces.ItableAttrGroup):
	__display_name__ = "table"	
	caption = schema.Object(Icaption, title='the table caption')
	col = schema.List(Icol, title='Table direct col (Must not contain any colgroup elements)', min_length=0, required=False)
	colgroup = schema.List(Icolgroup, title='Table direct colgroups (Must not contain any col elements)', min_length=0, required=False)
	thead = schema.Object(Ithead, title='table head', required=False)
	tfoot = schema.Object(Itfoot, title='table head', required=False)
	tbody = schema.List(Itbody, title='table body',  min_length=1, required=True)

# image Element

class Iimg(IatomicInline, attr_interfaces.IimgAttrGroup):
	__display_name__ = "img"

# hypertext Element

class Ia(IatomicInline, attr_interfaces.IaAttrGroup):
	__display_name__ = "a"

# math element

class Imath(IblockStatic, IflowStatic, IinlineStatic):
	__display_name__ = "math"

# variable element

class IfeedbackElement(attr_interfaces.IFeedbackAttrGroup):
	pass

class IfeedbackBlock(IfeedbackElement, IsimpleBlock):
	__display_name__ = "feedbackBlock"

class IfeedbackInline(IfeedbackElement, IsimpleInline):
	__display_name__ = "feedbackInline"
	
class IrubricBlock(attr_interfaces.IviewAttrGroup):
	__display_name__ = "rubricBlock"

# formatting items with stylesheets

class Istylesheet(attr_interfaces.IstylesheetAttrGroup):
	__display_name__ = "stylesheet"
	
class IitemBody(qti_interfaces.IbodyElement):
	__display_name__ = 'itemBody'
	blocks = schema.List(Iblock, title='The item body blocks', required=False)
