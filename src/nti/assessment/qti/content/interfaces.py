from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.schema import TextLineAttribute
from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.attributes import interfaces as atr_interfaces

class IObjectFlow(interface.Interface):
	__display_name__ = "objectFlow"

class IInline(interface.Interface):
	__display_name__ = 'inline'
			
class IBlock(interface.Interface):
	__display_name__ = 'block'
	
class IFlow(IObjectFlow):
	__display_name__ = "flow"
	base = TextLineAttribute(title='Base URI', required=False)
	
class IInlineStatic(IInline):
	__display_name__ = 'inlineStatic'
	
class IBlockStatic(IBlock):
	__display_name__= "blockStatic"
	
class IFlowStatic(IFlow):
	__display_name__ = "flowStatic"
	
class ISimpleInline(qti_interfaces.IBodyElement, IFlowStatic, IInlineStatic, IFiniteSequence):
	__display_name__ = "simpleInline"
	values = schema.List(IInline, 'inline objects contained', min_length=0)
	
class ISimpleBlock(IFlowStatic, qti_interfaces.IBodyElement, IBlockStatic, IFiniteSequence):
	__display_name__ = "simpleBlock"
	values = schema.List(IBlock, 'block objects contained', min_length=0)
	
class IAtomicInline(IFlowStatic, qti_interfaces.IBodyElement, IInlineStatic):
	__display_name__ = "atomicInline"
	
class IAtomicBlock(qti_interfaces.IBodyElement, IFlowStatic, IBlockStatic, IFiniteSequence):
	__display_name__ = "atomicBlock"
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
		
# Object elements

class IObject(qti_interfaces.IBodyElement, IFlowStatic, IInlineStatic, IFiniteSequence, atr_interfaces.IObjectAttrGroup):
	__display_name__ = "object"
	values = schema.List(IObjectFlow, 'objectflow elements contained', min_length=0)

class IParam(IObjectFlow, atr_interfaces.IParamAttrGroup):
	__display_name__ = "param"
	
	
	
	