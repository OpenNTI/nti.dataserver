# -*- coding: utf-8 -*-
"""
QIT schema field types

$Id: pyramid_views.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

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
	
@interface.implementer(IQTIAttribute)
class MimeTypeAttribute(TextLineAttribute):
	"""
	A :class: for mimetype attributes
	"""

@interface.implementer(IQTIAttribute)
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

