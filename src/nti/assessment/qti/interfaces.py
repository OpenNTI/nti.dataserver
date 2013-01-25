from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti.attributes import interfaces as atr_interfaces

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

# basic

class ITextOrVariable(interface.Interface):
	pass

class IbodyElement(atr_interfaces.IbodyElementAttrGroup):
	pass
		
class IAssessmentItem(atr_interfaces.IassessmentItemAttrGroup):
	"""
	Encompasses the information that is presented to a candidate and information about how to score the item.
	"""
	__display_name__ = 'assessmentItem'	
	#itemBody = schema.Object(IItemBody, title='The item body', required=False)
