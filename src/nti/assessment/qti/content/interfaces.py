from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.schema import TextLineAttribute
from nti.assessment.qti import interfaces as qti_interfaces

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
	
class IAtomicBlock(qti_interfaces.IBodyElement, IFlowStatic, IBlockStatic):
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
	
