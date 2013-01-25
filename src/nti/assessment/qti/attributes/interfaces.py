from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti import interfaces as qt_interfaces
from nti.assessment.qti.schema import (TextLineAttribute, BoolAttribute, IntAttribute, URIAttribute,
									   ChoiceAttribute, MimeTypeAttribute, ListAttribute)
	
class IAttrGroup(interface.interface):
	pass

# basic

class IBodyElementAttrGroup(IAttrGroup):
	id = TextLineAttribute(title=u'The element id', required=False)
	klass = TextLineAttribute(title=u'The class', required=False, __name__='class')
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2, default='en')
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

class IQAttrGroup(IAttrGroup):
	cite = URIAttribute(title=u'Citation URI', required=False)

class IBlockQuoteAttrGroup(IAttrGroup):
	cite = URIAttribute(title=u'Citation URI', required=False)
	
class IColAttrGroup(IAttrGroup):
	span = IntAttribute(title=u'The col span', required=False)

class IColGroupAttrGroup(IAttrGroup):
	span = IntAttribute(title=u'The col span', required=False)
	
class ITableAttrGroup(IAttrGroup):
	summary = TextLineAttribute(title=u'The table summary', required=False)
	
class ITableCellAttrGroup(IAttrGroup):
	headers = ListAttribute(title='Specifies one or more header cells a cell is related to', required=False,
							value_type=schema.TextLine(title='the header'))
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
	
class IFeedbackAttrGroup(IAttrGroup):
	outcomeIdentifier = TextLineAttribute(title="The identifier of an outcome", required=True)
	showHide = ChoiceAttribute(title="The visibility of the feedbackElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = TextLineAttribute(title="The identifier that determines the visibility of the feedback " +
								   "in conjunction with the showHide", required=True)
	
class IViewAttrGroup(IAttrGroup):
	view = TextLineAttribute(title="The views in which the rubric block's content are to be shown.", required=True)
	
class IStylesheetAttrGroup(IAttrGroup):
	href = URIAttribute(title='The identifier or location of the external stylesheet', required=True)
	type = MimeTypeAttribute(title="The mimeType", required=True)
	media = TextLineAttribute(title="An optional media descriptor", required=False)
	title = TextLineAttribute(title="An optional title for the stylesheet", required=False)

# interaction

class IInteractionAttrGroup(IAttrGroup):
	responseIdentifier = TextLineAttribute(title=u'The response identifier', required=True)
	
class IEndAttemptInteractionAttrGroup(IAttrGroup):
	title = TextLineAttribute(title="The string that should be displayed to the candidate as a prompt for ending the attempt using this interaction", required=True)
	
class IInlineChoiceInteractionAttrGroup(IAttrGroup):
	shuffle = BoolAttribute(title="If the shuffle attribute is true then the delivery engine must randomize the order in which the choices are " +
							"presented subject to the fixed attribute.", required=True)
	
	required = BoolAttribute(title="If true then a choice must be selected by the candidate in order to form a valid response to the interaction", required=False)
	
class IPromptAttrGroup(IBodyElementAttrGroup):
	pass
	
class IChoiceAttrGroup(IBodyElementAttrGroup):
	identifier = TextLineAttribute(title=u'The element identifier', required=True)
	fixed = BoolAttribute(title=u'Fixed choice attribute', required=False)
	templateIdentifier = TextLineAttribute(title=u'The template identifier', required=False)
	showHide = ChoiceAttribute(title="Determines how the visibility of the choice is controlled", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=False)

class ISimpleChoiceAttrGroup(IChoiceAttrGroup):
	pass

class IAssociableChoiceAttrGroup(IAttrGroup):
	matchGroup = ListAttribute(	title=u'A set of choices that this choice may be associated with, all others are excluded', required=False,
								value_type=schema.TextLine('the match group'))
	
class IChoiceInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True, default=1)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False, default=0)

class IAssociateInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxAssociations = IntAttribute(title=u'Max associations allowed', required=True)
	minAssociations = IntAttribute(title=u'Min associations allowed', required=False)

class ISimpleAssociableChoiceAttrGroup(IAttrGroup):
	matchMax = IntAttribute(title=u'The maximum number of choices this choice may be associated', required=True)
	matchMin = IntAttribute(title=u'The minimum number of choices this choice must be associated', required=False, default=0)

class IOrderInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=False)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False)
	orientation = ChoiceAttribute(title="Determines how the visibility of the choice is controlled",
								  vocabulary=qt_interfaces.ORIENTATION_TYPES_VOCABULARY, required=False)
	
class IMatchInteractioAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxAssociations = IntAttribute(title=u'The maximum number of associations', required=True, default=1)
	minAssociations = IntAttribute(title=u'The minimum number of associations', required=False, default=0)

class IGapMatchInteractioAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	
class IGapChoiceAttrGroup(IAttrGroup):
	matchMax = IntAttribute(title=u'The maximum number of choices this choice may be associated with', required=True)
	matchMin = IntAttribute(title=u'The minimum number of choices this choice may be associated with', required=False, default=0)
	
class IGapImgAttrGroup(IAttrGroup):
	objectLabel = TextLineAttribute(title=u'An optional label for the image object to be inserted', required=False)
	
class IGapAttrGroup(IAttrGroup):
	required = BoolAttribute(title=u'f true then this gap must be filled', required=False, default=False)
	
class IStringInteractionAttrGroup(IAttrGroup):
	base = IntAttribute(title=u'The number base', required=False)
	stringIdentifier = TextLineAttribute(title=u'The actual string entered by the candidate', required=False)
	expectedLength = IntAttribute(title=u'The hint to the expected length', required=False)
	patternMask = TextLineAttribute(title=u'The regular expression that the candidate must match', required=False)
	placeholderText = TextLineAttribute(title=u'Some placeholder text that can be used to vocalize the interactionh', required=False)

class IExtendedTextInteractionAttrGroup(IAttrGroup):
	maxStrings = IntAttribute(title=u'The maximum number of separate strings accepted', required=False)
	minStrings = IntAttribute(title=u'The minimum number of separate strings accepted', required=False)
	expectedLines  = IntAttribute(title=u'The expected number of lines of input required.', required=False)
	format = ChoiceAttribute(title="The format of the tex",
							 vocabulary=qt_interfaces.TEXT_FORMAT_TYPES_VOCABULARY, required=False)

class IHottextInteractionAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True, default=1)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False, default=0)

class IHotspotAttrGroup(IAttrGroup):
	shape = ChoiceAttribute(title="The shape of the hotspot",
							 vocabulary=qt_interfaces.SHAPE_TYPES_VOCABULARY, required=True) 
	coords = TextLineAttribute(title="The size and position of the hotspot, interpreted in conjunction with the shape",required=True) 
	hotspotLabel = TextLineAttribute(title="The alternative text for this (hot) area of the image",required=False, max_length=256) 

class IAssociableHotspotAttrGroup(IAttrGroup):
	matchMax = IntAttribute(title=u'The maximum number of choices this choice may be associated with', required=True)
	matchMin = IntAttribute(title=u'The minimum number of choices this choice may be associated with', required=False, default=0)
	
class IHotspotInteractiontAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'The maximum number of points that the candidate is allowed to select', required=True)
	minChoices = IntAttribute(title=u'The minimum number of points that the candidate is allowed to select', required=False, default=0)

class ISelectPointInteractionAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'The maximum number of points that the candidate is allowed to select', required=True)
	minChoices = IntAttribute(title=u'The minimum number of points that the candidate is allowed to select', required=False, default=0)
		
class IGraphicOrderInteractiontAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'The maximum number of choices to form a valid response to the interaction', required=False)
	minChoices = IntAttribute(title=u'The minimum number of choices to form a valid response to the interaction', required=False)

class IGraphicAssociateInteractiontAttrGroup(IAttrGroup):
	maxAssociations = IntAttribute(title=u'The maximum number of associations that the candidate is allowed to make', required=False, default=1)
	minAssociations = IntAttribute(title=u'The minimum number of associations that the candidate is required to make', required=False, default=0)
	
class IPositionObjectInteractiontAttrGroup(IAttrGroup):
	centerPoint = ListAttribute(title=u'Defines the point on the image being positioned', required=False, max_length=2, min_length=0,
								value_type=schema.Int(title='the value'))
	maxChoices = IntAttribute(title=u'The maximum number of points that the candidate is allowed to select', required=True)
	minChoices = IntAttribute(title=u'The minimum number of points that the candidate is allowed to select', required=False, default=0)

class IItemBodyAttrGroup(IBodyElementAttrGroup):
	pass

class IAssessmentItemAttrGroup(IAttrGroup):
	identifier = TextLineAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
