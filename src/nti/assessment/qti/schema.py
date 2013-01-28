from __future__ import unicode_literals, print_function

from zope import interface
from zope.schema import Int
from zope.schema import URI
from zope.schema import Bool
from zope.schema import List
from zope.schema import Float
from zope.schema import Choice
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
class URIAttribute(URI):
	"""
	A :class:`URI` type that to mark XML attribute elements
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

@interface.implementer(IQTIAttribute)
class IntAttribute(Int):
	"""
	A :class:`Int` type that to mark XML attribute elements
	"""

@interface.implementer(IQTIAttribute)
class FloatAttribute(Float):
	"""
	A :class:`Float` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class ChoiceAttribute(Choice):
	"""
	A :class:`Choice` type that to mark XML attribute elements
	"""
	
class MimeTypeAttribute(TextLineAttribute):
	"""
	A :class: for mimetype attributes
	"""

class ListAttribute(List):
	"""
	A :class:`List` type that to mark XML attribute elements
	"""

@interface.implementer(IQTIAttribute)
class IntegerOrVariableRefAttribute(Object):
	"""
	A :class:`Object` type that to mark XML attribute element for either an int or a variable ref
	"""
	
@interface.implementer(IQTIAttribute)
class FloatOrVariableRefAttribute(Object):
	"""
	A :class:`Object` type that to mark XML attribute element for either a float or a variable ref
	"""

@interface.implementer(IQTIAttribute)
class StringOrVariableRefAttribute(TextLineAttribute):
	pass

@interface.implementer(IQTIAttribute)
class IdentifierRefAttribute(TextLineAttribute):
	pass

