from __future__ import unicode_literals, print_function

from zope import interface

from nti.assessment.qti import interfaces as qt_interfaces
from nti.assessment.qti.schema import (TextLineAttribute, BoolAttribute, IntAttribute, URIAttribute,
									   ChoiceAttribute, MimeTypeAttribute)
	
class IAttrGroup(interface.interface):
	pass

# basic

class IBodyElementAttrGroup(IAttrGroup):
	id = TextLineAttribute(title=u'The element id', required=False)
	klass = TextLineAttribute(title=u'The class', required=False, __name__='class')
	lang = TextLineAttribute(title=u'The language code (RFC3066)', __name__='xml:lang', required=False, max_length=2, default='en')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	
# content

class IFlowAttrGroup(IAttrGroup):
	base = URIAttribute(title=u'The uri base', required=False, __name__='xml:base')
	
class IObjectAttrGroup(IAttrGroup):
	data =  URIAttribute(title='Provides a URI for locating the data associated with the object', required=True)
	type =  MimeTypeAttribute(title='The mimetype',required=True)
	width =  IntAttribute(title='The width', required=False)
	length =  IntAttribute(title='The length', required=False)

class IParamAttrGroup(IAttrGroup):
	name =  TextLineAttribute(title='The name of the parameter, as interpreted by the object', required=True)
	value =  TextLineAttribute(title='The value to pass to the object',required=True)
	valuetype = ChoiceAttribute(title="The param type", vocabulary=qt_interfaces.PARAM_TYPES_VOCABULARY)
	type =  MimeTypeAttribute(title='The mimetype',required=False)

class IColAttrGroup(IAttrGroup):
	span = IntAttribute(title=u'The col span', required=False)

class IColGroupAttrGroup(IAttrGroup):
	span = IntAttribute(title=u'The col span', required=False)
	
class ITableAttrGroup(IAttrGroup):
	summary = TextLineAttribute(title=u'The table summary', required=False)
	
class ITableCellAttrGroup(IAttrGroup):
	headers = TextLineAttribute(title='Specifies one or more header cells a cell is related to', required=False)
	scope = ChoiceAttribute(title="The param type", vocabulary=qt_interfaces.SCOPE_TABLE_TYPES, required=False)
	abbr = TextLineAttribute(title='Abbreviated version', required=False)
	axis = TextLineAttribute(title='Categorizes header cells', required=False)
	rowspan = IntAttribute(title='Specifies the number of rows a header cell should span', required=False)
	colspan = IntAttribute(title='Specifies the number of cols a header cell should span', required=False)

class IImgAttrGroup(IAttrGroup):
	src = URIAttribute(title='Image URI', required=True)
	alt = TextLineAttribute(title="The param type", max_length=256, required=False)
	longdesc = URIAttribute(title='Image URI', required=False)
	height = IntAttribute(title='Image heigth', required=False)
	width = IntAttribute(title='Image width', required=False)
	
class IAAttrGroup(IAttrGroup):
	href = URIAttribute(title='href URI', required=True)
	type = TextLineAttribute(title="The mimeType", required=False)
	
class IFeedBlackAttrGroup(IAttrGroup):
	outcomeIdentifier = TextLineAttribute(title="The identifier of an outcome", required=True)
	showHide = ChoiceAttribute(title="The visibility of the feedbackElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = TextLineAttribute(title="The identifier that determines the visibility of the feedback " +
								   "in conjunction with the showHide", required=True)
	
class IViewAttrGroup(IAttrGroup):
	view = TextLineAttribute(title="The views in which the rubric block's content are to be shown.", required=True)
	
class IStylesheetAttrGroup(IAttrGroup):
	href = URIAttribute(title='The identifier or location of the external stylesheet', required=True)
	type = TextLineAttribute(title="The mimeType", required=True)
	media = TextLineAttribute(title="An optional media descriptor", required=False)
	title = TextLineAttribute(title="An optional title for the stylesheet.", required=False)

# interaction

class IPromptAttrGroup(IBodyElementAttrGroup):
	pass
	
class IItemBodyAttrGroup(IBodyElementAttrGroup):
	pass

class IChoiceAttrGroup(IBodyElementAttrGroup):
	identifier = TextLineAttribute(title=u'The element identifier', required=True)
	fixed = BoolAttribute(title=u'Fixed choice attribute', required=False)
	templateIdentifier = TextLineAttribute(title=u'The template identifier', required=False)
	showHide = BoolAttribute(title=u'Show hide flag', required=False)

class ISimpleChoiceAttrGroup(IChoiceAttrGroup):
	pass

class IInteractionAttrGroup(IBodyElementAttrGroup):
	responseIdentifier = TextLineAttribute(title=u'The response identifier', required=True)

class IBlockInteractionAttrGroup(IFlowAttrGroup, IInteractionAttrGroup):
	pass
	
class IChoiceInteractionAttrGroup(IFlowAttrGroup, IInteractionAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False)

class IAssessmentItemAttrGroup(IAttrGroup):
	identifier = TextLineAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
