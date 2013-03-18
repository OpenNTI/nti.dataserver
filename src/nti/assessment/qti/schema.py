# -*- coding: utf-8 -*-
"""
QIT schema field types

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six
import numbers
from collections import Iterable

from zope import schema
from zope import interface
from zope.schema import interfaces as schema_interfaces

from nti.utils import schema as nti_schema

class IQTIAttribute(interface.Interface):
	"""
	Marker interface for QTI [XML] attributes
	"""

	def toUnicode(value):
		"""
		Transform the specified value to unicode
		"""

@interface.implementer(IQTIAttribute)
class BaseQTIAttribute(object):

	def fromUnicode(self, value):
		result = super(BaseQTIAttribute, self).fromUnicode(value) if value else None
		return result

	def toUnicode(self, value):
		return unicode(value) if value is not None else None

class TextLineAttribute(BaseQTIAttribute, nti_schema.ValidTextLine):
	"""
	A :class:`schema.TextLine` type that to mark XML attribute elements
	"""

class URIAttribute(BaseQTIAttribute, nti_schema.ValidURI):
	"""
	A :class:`schema.URI` type that to mark XML attribute elements
	"""

@interface.implementer(schema_interfaces.IFromUnicode)
class BoolAttribute(BaseQTIAttribute, schema.Bool):
	"""
	A :class:`schema.Bool` type that to mark XML attribute elements
	"""

class IntAttribute(BaseQTIAttribute, schema.Int):
	"""
	A :class:`schema.Int` type that to mark XML attribute elements
	"""

class FloatAttribute(BaseQTIAttribute, nti_schema.Number):
	"""
	A :class:`schema.Float` type that to mark XML attribute elements
	"""

class ChoiceAttribute(BaseQTIAttribute, schema.Choice):
	"""
	A :class:`schema.Choice` type that to mark XML attribute elements
	"""

class MimeTypeAttribute(TextLineAttribute):
	"""
	A :class: for mimetype attributes
	"""

@interface.implementer(schema_interfaces.IFromUnicode)
class ListAttribute(BaseQTIAttribute, schema.List):
	"""
	A :class:`schema.List` type that to mark XML attribute elements
	"""

	pattern = re.compile("[^\s]+")

	def fromUnicode(self, value):
		result = []
		for p in self.pattern.findall(value or ''):
			result.append(self.value_type.fromUnicode(p))
		return result

	def toUnicode(self, value):
		if isinstance(value, six.string_types):
			result = unicode(value)
		elif isinstance(value, Iterable):
			func = unicode if not IQTIAttribute.providedBy(self.value_type) else self.value_type.toUnicode
			result = [func(x) for x in value]
			result = ' '.join(result)
		else:
			result = super(ListAttribute, self).toUnicode(value)
		return result

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
		result = super(IntegerOrVariableRefAttribute, self).fromUnicode(value)
		if result:
			try:
				result = int(result)
			except:
				result = unicode(result)
		return result

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
		result = super(FloatOrVariableRefAttribute, self).fromUnicode(value)
		if result:
			try:
				result = float(result)
			except:
				result = unicode(result)
		return result

	def constraint(self, value):
		if isinstance(value, six.string_types):
			return '\n' not in value and '\r' not in value
		return isinstance(value, (numbers.Integral, numbers.Real))

class StringOrVariableRefAttribute(TextLineAttribute):
	pass

class IdentifierRefAttribute(TextLineAttribute):
	pass

