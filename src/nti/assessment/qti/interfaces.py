from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti.schema import (TextLineAttribute, BoolAttribute)

# xml node

class _XmlNode(interface.Interface):
	"""
	Marker interface for XML bound objects
	"""
	pass

class IAttribute(interface.Interface):
	parent = schema.Object(_XmlNode, title=u'Parent of this attribute', required=True)
	name = schema.TextLine(title=u'Parent of this attribute', required=True)
	
class IXmlNode(_XmlNode):
	parent = schema.Object(_XmlNode, title=u'Parent of this node', required=False)

	def getParentRoot():
		"""
		Root of this node or node itself
		"""
# basic

class ITextOrVariable(interface.Interface):
	__display_name__ = 'textOrVariable'

class IBlock(interface.Interface):
	__display_name__ = 'block'
	
class IInline(interface.Interface):
	__display_name__ = 'inline'
		
class IObjectFlow(interface.Interface):
	__display_name__ = "objectFlow";

class IFlow(IObjectFlow):
	__display_name__ = "flow";
	
class IFlowStatic(IFlow):
	__display_name__ = "flowStatic";
		
class IBlockStatic(IBlock):
	__display_name__= "blockStatic";
	
class IAtomicBlock(IFlowStatic, IBlockStatic):
	__display_name__ = "atomicBlock"

class IInlineStatic(IInline):
	__display_name__ = 'inlineStatic'
	
class IAtomicInline(IFlowStatic, IInlineStatic):
	__display_name__ = "atomicInline"

class ISimpleBlock(IFlowStatic, IBlockStatic):
	__display_name__ = "simpleBlock";
		
class ISimpleInline(IFlowStatic, IInlineStatic):
	__display_name__ = "simpleInline"
	
class ITextRun(IFlowStatic, IInlineStatic, ITextOrVariable):
	__display_name__ = "textRun"
	
class IItemBody(interface.Interface):
	"""
	Describe the item's content and information
	"""
	__display_name__ = 'itemBody'
	
	blocks = schema.List(IBlock, title='The item body blocks', required=False)
	
class IAssessmentItem(interface.Interface):
	"""
	Encompasses the information that is presented to a candidate and information about how to score the item.
	"""
	__display_name__ = 'assessmentItem'
	
	identifier = TextLineAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
	itemBody = schema.Object(IItemBody, title='The item body', required=False)
