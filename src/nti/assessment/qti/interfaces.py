from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti.attributes import interfaces as atr_interfaces

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

class IBodyElement(atr_interfaces.IBodyElementAttrGroup):
	__display_name__ = 'bodyElement'
	
class IItemBody(interface.Interface):
	"""
	Describe the item's content and information
	"""
	__display_name__ = 'itemBody'
	
	blocks = schema.List(IBlock, title='The item body blocks', required=False)
	
class IAssessmentItem(atr_interfaces.IAssessmentItemAttrGroup):
	"""
	Encompasses the information that is presented to a candidate and information about how to score the item.
	"""
	__display_name__ = 'assessmentItem'	
	itemBody = schema.Object(IItemBody, title='The item body', required=False)
