#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility classes and methods for working with zope schemas.

Also patches a bug in the :class:`dm.zope.schema.schema.Object` class
that requires the default value for ``check_declaration`` to be specified;
thus always import `Object` from this module.

.. todo:: This module is big enough it should be factored into a package and sub-modules.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)



from nti.schema.fieldproperty import AcquisitionFieldProperty
from nti.schema.fieldproperty import AdaptingFieldProperty
from nti.schema.fieldproperty import AdaptingFieldPropertyStoredThroughField
from nti.schema.interfaces import BeforeCollectionAssignedEvent
from nti.schema.interfaces import BeforeDictAssignedEvent
from nti.schema.interfaces import BeforeObjectAssignedEvent
from nti.schema.interfaces import BeforeSchemaFieldAssignedEvent
from nti.schema.interfaces import BeforeSequenceAssignedEvent
from nti.schema.interfaces import BeforeSetAssignedEvent
from nti.schema.interfaces import BeforeTextAssignedEvent
from nti.schema.interfaces import BeforeTextLineAssignedEvent
from nti.schema.field import Bool
from nti.schema.field import Choice
from nti.schema.vocabulary import CountryTerm
from nti.schema.vocabulary import CountryVocabularyFactory
from nti.schema.field import Date
from nti.schema.field import DateTime
from nti.schema.field import Datetime
from nti.schema.field import Decimal
from nti.schema.field import DecodingValidTextLine
from nti.schema.field import Dict
from nti.schema.field import DictFromObject
from nti.schema.schema import EqHash
from nti.schema.fieldproperty import FieldProperty
from nti.schema.fieldproperty import FieldPropertyStoredThroughField
from nti.schema.field import FieldValidationMixin
from nti.schema.field import Float
from nti.schema.field import FrozenSet
from nti.schema.field import HTTPURL
from nti.schema.fieldproperty import IAcquirer
from nti.schema.interfaces import IBeforeCollectionAssignedEvent
from nti.schema.interfaces import IBeforeContainerAssignedEvent
from nti.schema.interfaces import IBeforeDictAssignedEvent
from nti.schema.interfaces import IBeforeIterableAssignedEvent
from nti.schema.interfaces import IBeforeSchemaFieldAssignedEvent
from nti.schema.interfaces import IBeforeSequenceAssignedEvent
from nti.schema.interfaces import IBeforeSetAssignedEvent
from nti.schema.interfaces import IBeforeTextAssignedEvent
from nti.schema.interfaces import IBeforeTextLineAssignedEvent
from nti.schema.interfaces import IFromObject
from nti.schema.interfaces import IVariant
from nti.schema.field import IndexedIterable
from nti.schema.field import Int
from nti.schema.interfaces import InvalidValue
from nti.schema.field import Iterable
from nti.schema.field import List
from nti.schema.field import ListOrTuple
from nti.schema.field import ListOrTupleFromObject
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ObjectBase
from nti.schema.field import ObjectLen
from nti.schema.schema import PermissiveSchemaConfigured
from nti.schema.field import SchemaConfigured
from nti.schema.field import Set
from nti.schema.field import Text
from nti.schema.field import TextLine
from nti.schema.field import Timedelta
from nti.schema.field import Tuple
from nti.schema.field import TupleFromObject
from nti.schema.fieldproperty import UnicodeConvertingFieldProperty
from nti.schema.field import UniqueIterable
from nti.schema.field import ValidBytes
from nti.schema.field import ValidBytesLine
from nti.schema.field import ValidChoice
from nti.schema.field import ValidDatetime
from nti.schema.field import ValidRegEx
from nti.schema.field import ValidRegularExpression
from nti.schema.field import ValidSet
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine
from nti.schema.field import ValidURI
from nti.schema.field import Variant
from nti.schema.vocabulary import _CountryVocabulary
from nti.schema.vocabulary import _ICountryAvailability
from nti.schema.field import _SequenceFromObjectMixin
from nti.schema.vocabulary import _SimpleTerm
from nti.schema.vocabulary import _SimpleVocabulary
from nti.schema.field import _ValueTypeAddingDocMixin
from nti.schema.field import _do_set
from nti.schema.fieldproperty import createDirectFieldProperties
from nti.schema.fieldproperty import createFieldProperties
from nti.schema.interfaces import find_most_derived_interface
from nti.schema.schema import schemadict

from . import dataurl

class DataURI(ValidURI):
	"""
	A URI field that ensures and requires its value to be
	a data URI. The field value is a :class:`.DataURL`.
	"""

	def _validate(self, value):
		super(DataURI,self)._validate(value)
		if not value.startswith(b'data:'):
			self._reraise_validation_error( sch_interfaces.InvalidURI(value),
											value,
											_raise=True )

	def fromUnicode( self, value ):
		if isinstance(value,dataurl.DataURL):
			return value

		super(DataURI, self).fromUnicode(value)
		return dataurl.DataURL(value)

from zope.deprecation import deprecated
deprecated('AcquisitionFieldProperty', 'Moved to nti.schema')
deprecated('AdaptingFieldProperty', 'Moved to nti.schema')
deprecated('AdaptingFieldPropertyStoredThroughField', 'Moved to nti.schema')
deprecated('BeforeCollectionAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeDictAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeObjectAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeSchemaFieldAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeSequenceAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeSetAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeTextAssignedEvent', 'Moved to nti.schema')
deprecated('BeforeTextLineAssignedEvent', 'Moved to nti.schema')
deprecated('Bool', 'Moved to nti.schema')
deprecated('Choice', 'Moved to nti.schema')
deprecated('CountryTerm', 'Moved to nti.schema')
deprecated('CountryVocabularyFactory', 'Moved to nti.schema')
deprecated('DataURI', 'Moved to nti.schema')
deprecated('Date', 'Moved to nti.schema')
deprecated('DateTime', 'Moved to nti.schema')
deprecated('Datetime', 'Moved to nti.schema')
deprecated('Decimal', 'Moved to nti.schema')
deprecated('DecodingValidTextLine', 'Moved to nti.schema')
deprecated('Dict', 'Moved to nti.schema')
deprecated('DictFromObject', 'Moved to nti.schema')
deprecated('EqHash', 'Moved to nti.schema')
deprecated('FieldProperty', 'Moved to nti.schema')
deprecated('FieldPropertyStoredThroughField', 'Moved to nti.schema')
deprecated('FieldValidationMixin', 'Moved to nti.schema')
deprecated('Float', 'Moved to nti.schema')
deprecated('FrozenSet', 'Moved to nti.schema')
deprecated('HTTPURL', 'Moved to nti.schema')
deprecated('IAcquirer', 'Moved to nti.schema')
deprecated('IBeforeCollectionAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeContainerAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeDictAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeIterableAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeSchemaFieldAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeSequenceAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeSetAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeTextAssignedEvent', 'Moved to nti.schema')
deprecated('IBeforeTextLineAssignedEvent', 'Moved to nti.schema')
deprecated('IFromObject', 'Moved to nti.schema')
deprecated('IVariant', 'Moved to nti.schema')
deprecated('IndexedIterable', 'Moved to nti.schema')
deprecated('Int', 'Moved to nti.schema')
deprecated('InvalidValue', 'Moved to nti.schema')
deprecated('Iterable', 'Moved to nti.schema')
deprecated('List', 'Moved to nti.schema')
deprecated('ListOrTuple', 'Moved to nti.schema')
deprecated('ListOrTupleFromObject', 'Moved to nti.schema')
deprecated('Number', 'Moved to nti.schema')
deprecated('Object', 'Moved to nti.schema')
deprecated('ObjectBase', 'Moved to nti.schema')
deprecated('ObjectLen', 'Moved to nti.schema')
deprecated('PermissiveSchemaConfigured', 'Moved to nti.schema')
deprecated('SchemaConfigured', 'Moved to nti.schema')
deprecated('Set', 'Moved to nti.schema')
deprecated('Text', 'Moved to nti.schema')
deprecated('TextLine', 'Moved to nti.schema')
deprecated('Timedelta', 'Moved to nti.schema')
deprecated('Tuple', 'Moved to nti.schema')
deprecated('TupleFromObject', 'Moved to nti.schema')
deprecated('UnicodeConvertingFieldProperty', 'Moved to nti.schema')
deprecated('UniqueIterable', 'Moved to nti.schema')
deprecated('ValidBytes', 'Moved to nti.schema')
deprecated('ValidBytesLine', 'Moved to nti.schema')
deprecated('ValidChoice', 'Moved to nti.schema')
deprecated('ValidDatetime', 'Moved to nti.schema')
deprecated('ValidRegEx', 'Moved to nti.schema')
deprecated('ValidRegularExpression', 'Moved to nti.schema')
deprecated('ValidSet', 'Moved to nti.schema')
deprecated('ValidText', 'Moved to nti.schema')
deprecated('ValidTextLine', 'Moved to nti.schema')
deprecated('ValidURI', 'Moved to nti.schema')
deprecated('Variant', 'Moved to nti.schema')
deprecated('_CountryVocabulary', 'Moved to nti.schema')
deprecated('_ICountryAvailability', 'Moved to nti.schema')
deprecated('_SequenceFromObjectMixin', 'Moved to nti.schema')
deprecated('_SimpleTerm', 'Moved to nti.schema')
deprecated('_SimpleVocabulary', 'Moved to nti.schema')
deprecated('_ValueTypeAddingDocMixin', 'Moved to nti.schema')
deprecated('_do_set', 'Moved to nti.schema')
deprecated('absolute_import', 'Moved to nti.schema')
deprecated('aq_base', 'Moved to nti.schema')
deprecated('before_object_assigned_event_dispatcher', 'Moved to nti.schema')
deprecated('createDirectFieldProperties', 'Moved to nti.schema')
deprecated('createFieldProperties', 'Moved to nti.schema')
deprecated('find_most_derived_interface', 'Moved to nti.schema')
deprecated('sch_interfaces', 'Moved to nti.schema')
deprecated('schema', 'Moved to nti.schema')
deprecated('schemadict', 'Moved to nti.schema')
