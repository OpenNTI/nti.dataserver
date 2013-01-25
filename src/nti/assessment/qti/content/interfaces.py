from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.schema import TextLineAttribute
from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.attributes import interfaces as atr_interfaces
	
class IObjectFlow(interface.Interface):
	pass

class IInline(interface.Interface):
	pass
			
class IBlock(interface.Interface):
	pass
	
class IFlow(IObjectFlow, atr_interfaces.IFlowAttrGroup):
	pass
	
class IInlineStatic(IInline):
	pass
	
class IBlockStatic(IBlock):
	pass
	
class IFlowStatic(IFlow):
	pass
	
class ISimpleInline(qti_interfaces.IBodyElement, IFlowStatic, IInlineStatic, IFiniteSequence):
	values = schema.List(IInline, 'inline objects contained', min_length=0)
	
class ISimpleBlock(IFlowStatic, qti_interfaces.IBodyElement, IBlockStatic, IFiniteSequence):
	values = schema.List(IBlock, 'block objects contained', min_length=0)
	
class IAtomicInline(IFlowStatic, qti_interfaces.IBodyElement, IInlineStatic):
	pass
	
class IAtomicBlock(qti_interfaces.IBodyElement, IFlowStatic, IBlockStatic, IFiniteSequence):
	values = schema.List(IInline, 'inline objects contained', min_length=0)

class ITextRun(IFlowStatic, IInlineStatic, qti_interfaces.ITextOrVariable):
	__display_name__ = "textRun"
	
class IAbbr(ISimpleInline):
	__display_name__ = "abbr"
	
class IAcronym(ISimpleInline):
	__display_name__ = "acronym"
	
class IAddress(IAtomicBlock):
	__display_name__ = "address"

class IBlockQuote(ISimpleBlock):
	__display_name__ = "blockquote"
	cite = TextLineAttribute(title='Citation URI', required=False)
	
class IBr(IAtomicInline):
	__display_name__ = "br"
	
class ICite(ISimpleInline):
	__display_name__ = "cite"
	
class ICode(ISimpleInline):
	__display_name__ = "code"
	
class IDfn(ISimpleInline):
	__display_name__ = "dfn"
	
class IDiv(IFlowStatic, qti_interfaces.IBodyElement, IBlockStatic, IFiniteSequence):
	__display_name__ = "div"
	values = schema.List(IFlow, 'inline objects contained', min_length=0)
	
class IEm(ISimpleInline):
	__display_name__ = "em"
	
class IH1(IAtomicBlock):
	__display_name__ = "h1"

class IH2(IAtomicBlock):
	__display_name__ = "h2"

class IH3(IAtomicBlock):
	__display_name__ = "h3"		
	
class IH4(IAtomicBlock):
	__display_name__ = "h4"
	
class IH5(IAtomicBlock):
	__display_name__ = "h5"
	
class IH6(IAtomicBlock):
	__display_name__ = "h6"
	
class IKbd(ISimpleInline):
	__display_name__ = "kbd"
	
class IP(IAtomicBlock):
	__display_name__ = "p"
	
class IPre(IAtomicBlock):
	"""
	Although pre inherits from atomicBlock it must not contain, either directly or indirectly,
	any of the following objects: img, object, big, small, sub, sup.
	"""
	__display_name__ = "pre"
	
class IQ(ISimpleInline):
	__display_name__ = "q"
	cite = TextLineAttribute(title='Citation URI', required=False)
	
class ISamp(ISimpleInline):
	__display_name__ = "samp"
	
class ISpan(ISimpleInline):
	__display_name__ = "span"

class IStrong(ISimpleInline):
	__display_name__ = "strong"
	
class IVar(ISimpleInline):
	__display_name__ = "var"

# list elements

class IDLElement(qti_interfaces.IBodyElement):
	pass

class IDL(IBlockStatic, qti_interfaces.IBodyElement, IFlowStatic, IFiniteSequence):
	__display_name__ = "dl"
	values = schema.List(IDLElement, 'dl elements contained', min_length=0)
	
class IDT(IDLElement, IFiniteSequence):
	__display_name__ = "dt"
	values = schema.List(IInline, 'inline elements contained', min_length=0)

class IDD(IDLElement, IFiniteSequence):
	__display_name__ = "dd"
	values = schema.List(IFlow, 'flow elements contained', min_length=0)

class IIL(qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "il"
	values = schema.List(IFlow, 'flow elements contained', min_length=0)

class IOL(IBlockStatic, qti_interfaces.IBodyElement, IFlowStatic, IFiniteSequence):
	__display_name__ = "ol"
	values = schema.List(IIL, 'il elements contained', min_length=0)
	
class IUL(IBlockStatic, qti_interfaces.IBodyElement, IFlowStatic, IFiniteSequence):
	__display_name__ = "ul"
	values = schema.List(IIL, 'il elements contained', min_length=0)
		
# object elements

class IObject(qti_interfaces.IBodyElement, IFlowStatic, IInlineStatic, IFiniteSequence, atr_interfaces.IObjectAttrGroup):
	__display_name__ = "object"
	values = schema.List(IObjectFlow, 'objectflow elements contained', min_length=0)

class IParam(IObjectFlow, atr_interfaces.IParamAttrGroup):
	__display_name__ = "param"
	
# presentation Elements

class IB(ISimpleInline):
	__display_name__ = "b"

class IBig(ISimpleInline):
	__display_name__ = "big"	

class IHr(IBlockStatic, qti_interfaces.IBodyElement, IFlowStatic):
	__display_name__ = "hr"	

class II(ISimpleInline):
	__display_name__ = "i"	

class ISmall(ISimpleInline):
	__display_name__ = "small"	

class ISub(ISimpleInline):
	__display_name__ = "sub"	

class ISup(ISimpleInline):
	__display_name__ = "sup"	

class ITt(ISimpleInline):
	__display_name__ = "tt"	

# table elements

class ICaption(qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "caption"	
	values = schema.List(IInline, 'inline elements contained', min_length=0)

class ICol(qti_interfaces.IBodyElement, atr_interfaces.IColAttrGroup):
	__display_name__ = "col"	
	
class IColGroup(qti_interfaces.IBodyElement, atr_interfaces.IColGroupAttrGroup, IFiniteSequence):
	__display_name__ = "colgroup"	
	values = schema.List(ICol, 'inline elements contained', min_length=0)

class ITableCell(qti_interfaces.IBodyElement, atr_interfaces.ITableCellAttrGroup, IFiniteSequence):
	values = schema.List(IFlow, 'inline elements contained', min_length=0)

class ITd(ITableCell):
	__display_name__ = "td"	
	
class ITh(ITableCell):
	__display_name__ = "th"	
	
class ITr( qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "tr"
	values = schema.List(ITableCell, 'tableCell elements contained', min_length=0)
	
class IThead( qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "thead"
	values = schema.List(ITr, 'tr elements contained', min_length=1)
	
class ITFoot( qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "tfoot"
	values = schema.List(ITr, 'tr elements contained', min_length=1)
	
class ITBody( qti_interfaces.IBodyElement, IFiniteSequence):
	__display_name__ = "tbody"
	values = schema.List(ITr, 'tr elements contained', min_length=1)
	
class ITable(IBlockStatic, qti_interfaces.IBodyElement, IFlowStatic, atr_interfaces.ITableAttrGroup):
	__display_name__ = "table"	
	caption = schema.Object(ICaption, title='the table caption')
	col = schema.List(ICol, title='Table direct col (Must not contain any colgroup elements)', min_length=0, required=False)
	colgroup = schema.List(IColGroup, title='Table direct colgroups (Must not contain any col elements)', min_length=0, required=False)
	thead = schema.Object(IThead, title='table head', required=False)
	tfoot = schema.Object(ITFoot, title='table head', required=False)
	tbody = schema.List(ITBody, title='table body',  min_length=1, required=True)

# image Element

class IImg(IAtomicInline, atr_interfaces.IImgAttrGroup):
	__display_name__ = "img"

# hypertext Element

class IA(IAtomicInline, atr_interfaces.IAAttrGroup):
	__display_name__ = "a"

# math element

class IMath(IBlockStatic, IFlowStatic, IInlineStatic):
	__display_name__ = "math"

	
# variable element

class IFeedbackElement(atr_interfaces.IFeedBlackAttrGroup):
	pass

class IFeedbackBlock(IFeedbackElement, ISimpleBlock):
	__display_name__ = "feedbackBlock"

class IFeedbackInline(IFeedbackElement, ISimpleInline):
	__display_name__ = "feedbackInline"
	
class IRubricBlock(atr_interfaces.IViewAttrGroup):
	__display_name__ = "rubricBlock"

# formatting items with stylesheets

class IStylesheet(atr_interfaces.IStylesheetAttrGroup):
	__display_name__ = "stylesheet"
	
class IItemBody(qti_interfaces.IBodyElement):
	__display_name__ = 'itemBody'
	blocks = schema.List(IBlock, title='The item body blocks', required=False)
