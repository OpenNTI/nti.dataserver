# -*- coding: utf-8 -*-
"""
QIT schema field types

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import numbers

from zope import schema
from zope import interface
from zope.schema import interfaces as schema_interfaces

class IQTIAttribute(interface.Interface):
	"""
	Marker interface for QTI [XML] attributes
	"""
	pass

@interface.implementer(IQTIAttribute)
class TextLineAttribute(schema.TextLine):
	"""
	A :class:`schema.TextLine` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class URIAttribute(schema.URI):
	"""
	A :class:`schema.URI` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class BoolAttribute(schema.Bool):
	"""
	A :class:`schema.Bool` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class ObjectAttribute(schema.Object):
	"""
	A :class:`schema.Object` type that to mark XML attribute elements
	"""

@interface.implementer(IQTIAttribute)
class IntAttribute(schema.Int):
	"""
	A :class:`schema.Int` type that to mark XML attribute elements
	"""

@interface.implementer(IQTIAttribute)
class FloatAttribute(schema.Float):
	"""
	A :class:`schema.Float` type that to mark XML attribute elements
	"""
	
@interface.implementer(IQTIAttribute)
class ChoiceAttribute(schema.Choice):
	"""
	A :class:`schema.Choice` type that to mark XML attribute elements
	"""
	
class MimeTypeAttribute(TextLineAttribute):
	"""
	A :class: for mimetype attributes
	"""

@interface.implementer(IQTIAttribute)
class ListAttribute(schema.List):
	"""
	A :class:`schema.List` type that to mark XML attribute elements
	"""

class IntegerOrVariableRefAttribute(TextLineAttribute):
	
	"""
	A :class: to mark XML an attribute element for either an schema.Int or a variable ref (string)
	"""
	def _validate(self, value):
		if not (isinstance(value, six.string_types) or isinstance(value, numbers.Integral)):
			raise schema_interfaces.WrongType(value)

		if not self.constraint(value):
			raise schema_interfaces.ConstraintNotSatisfied(value)
		
	def fromUnicode(self, value):
		s = super(IntegerOrVariableRefAttribute, self).fromUnicode(value)
		try:
			value = int(s)
		except:
			value = unicode(s)
		return value
	
	def constraint(self, value):
		if isinstance(value, six.string_types):
			return '\n' not in value and '\r' not in value
		return isinstance(value, numbers.Integral)
	
class FloatOrVariableRefAttribute(TextLineAttribute):
	"""
	A :class: to mark XML attribute element for either a schema.Float or a variable ref (string)
	"""
	def _validate(self, value):
		if not (isinstance(value, six.string_types) or isinstance(value, (numbers.Integral, numbers.Real))):
			raise schema_interfaces.WrongType(value)

		if not self.constraint(value):
			raise schema_interfaces.ConstraintNotSatisfied(value)
		
	def fromUnicode(self, value):
		s = super(IntegerOrVariableRefAttribute, self).fromUnicode(value)
		try:
			value = float(s)
		except:
			value = unicode(s)
		return value
	
	def constraint(self, value):
		if isinstance(value, six.string_types):
			return '\n' not in value and '\r' not in value
		return isinstance(value, (numbers.Integral, numbers.Real))
	
class StringOrVariableRefAttribute(TextLineAttribute):
	pass

class IdentifierRefAttribute(TextLineAttribute):
	pass

