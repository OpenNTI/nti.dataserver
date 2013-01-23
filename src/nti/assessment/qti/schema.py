from __future__ import unicode_literals, print_function

from zope import interface
from zope.schema import Bool
from zope.schema import Object
from zope.schema import TextLine

class IQTIAttribute(interface.Interface):
	"""
	Marker interface for QTI [XML] attributes
	"""
	pass

@interface.implementer(IQTIAttribute)
class TextLineAttribute(TextLine):
	"""
	A :class:`TextLine` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class BoolAttribute(Bool):
	"""
	A :class:`Bool` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class ObjectAttribute(Object):
	"""
	A :class:`Object` type that to mark XML attribute elements
	"""
