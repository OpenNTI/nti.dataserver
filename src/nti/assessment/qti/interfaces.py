from __future__ import unicode_literals, print_function

from zope import schema

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

