# -*- coding: utf-8 -*-
"""
QTI Base interfaces

$Id: interfaces.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

# vocabulary

PARAM_TYPES = (u'DATA', u'REF')
PARAM_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in PARAM_TYPES] )

SCOPE_TABLE_TYPES = (u'col', u'colgroup', u'row', u'rowgroup')
SCOPE_TABLE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in SCOPE_TABLE_TYPES] )

SHOW_HIDE_TYPES = (u'show', u'hide')
SHOW_HIDE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in SHOW_HIDE_TYPES] )

VIEW_TYPES = (u'author', u'candidate', u'proctor', u'scorer', u'testConstructor', u'tutor')
VIEW_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in VIEW_TYPES] )

ORIENTATION_TYPES = (u'vertial', u'horizontal')
ORIENTATION_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in ORIENTATION_TYPES] )

TEXT_FORMAT_TYPES = (u'plain', u'preFormatted', u'xhtml')
TEXT_FORMAT_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in TEXT_FORMAT_TYPES] )

SHAPE_TYPES = (u'default', u'rect', u'circle', u'poly', u'ellipse')
SHAPE_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in SHAPE_TYPES] )

VALUE_TYPES = (	u'identifier', u'boolean', u'integer', u'float', u'string', u'point', u'pair', u'directedPair', u'duration',
				u'file', u'uri', u'intOrIdentifier')
VALUE_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in VALUE_TYPES] )

CARDINALITY_TYPES = (u'single', u'multiple', u'ordered', u'record')
CARDINALITY_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in CARDINALITY_TYPES] )

NAVIGATION_MODE_TYPES = (u'linear', u'nonlinear')
NAVIGATION_MODE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in NAVIGATION_MODE_TYPES] )

SUBMISSION_MODE_TYPES = (u'individual', u'simultaneous')
SUBMISSION_MODE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in SUBMISSION_MODE_TYPES] )

FEED_BACK_ACCESS_TYPES = (u'atEnd', u'during')
FEED_BACK_ACCESS_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in FEED_BACK_ACCESS_TYPES] )

BASE_TYPES = VALUE_TYPES
BASE_TYPES_VOCABULARY = VALUE_TYPES_VOCABULARY

MATH_CONSTANTS_TYPES = (u'pi', u'e')
MATH_CONSTANTS_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in MATH_CONSTANTS_TYPES] )

STAT_OPERATOR_NAMES = (u'mean', u'sampleVariance', u'sampleSD', u'popVariance', u'popSD')
STAT_OPERATOR_NAMES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in STAT_OPERATOR_NAMES] )

ROUNDING_MODE_TYPES = (u'significantFigures', u'decimalPlaces')
ROUNDING_MODE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in ROUNDING_MODE_TYPES] )

MATH_OPERATORS_TYPES = (u'sin', u'decimalPlaces', u'cos', u'tan',u'sec', u'csc',u'cot', u'asin',
						u'acos', u'atan', u'atan2', u'asec', u'acsc', u'acot', u'sinh', u'cosh',
						u'tanh', u'sech', u'csch', u'coth', u'log', u'ln', u'exp', u'abs',
						u'signum', u'floor', u'ceil', u'toDegrees', u'toRadians')
MATH_OPERATORS_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in MATH_OPERATORS_TYPES] )


TOLERANCE_MODE_TYPES = (u'exact', u'relative', u'absolute')
TOLERANCE_MODE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in TOLERANCE_MODE_TYPES] )

DATA_TYPES = (u'boolean', u'coords', u'datetime', u'duration',u'float', u'identifier', u'integer', u'language',
			  u'length', u'mimeType', u'orientation', u'string', u'string256', u'styleclass', u'valueType', u'view')
DATA_TYPES_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in DATA_TYPES] )

# interfaces

class IConcrete(interface.Interface):
	"""
	Marker interface for concreate QTI classes
	"""
	__display_name__ = interface.Attribute("Display name")

