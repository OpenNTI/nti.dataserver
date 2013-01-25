from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti import interfaces as qt_interfaces
from nti.assessment.qti.schema import (TextLineAttribute, BoolAttribute, IntAttribute, URIAttribute,
									   ChoiceAttribute, MimeTypeAttribute, ListAttribute, FloatAttribute,
									   ObjectAttribute)
	
class IAttrGroup(interface.interface):
	pass

# basic

class IbodyElementAttrGroup(IAttrGroup):
	id = TextLineAttribute(title=u'The element id', required=False)
	klass = TextLineAttribute(title=u'The class', required=False, __name__='class')
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2, default='en')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	
# variables

class IvalueAttrGroup(IAttrGroup):
	fieldIdentifier = TextLineAttribute(title=u'The field id', required=False)
	baseType = ChoiceAttribute(title="The base-type", vocabulary=qt_interfaces.VALUE_TYPES_VOCABULARY, required=False)
	
class IdefaultValueAttrGroup(IAttrGroup):
	interpretation = TextLineAttribute(title=u'A human readable interpretation of the default value', required=False)
	
class IvalueDeclarationAttrGroup(IAttrGroup):
	identifier = TextLineAttribute(title=u'The id', required=True)
	cardinality = ChoiceAttribute(title="The variable cardinality", vocabulary=qt_interfaces.CARDINALITY_TYPES_VOCABULARY, required=True)
	baseType = ChoiceAttribute(title="The base-type", vocabulary=qt_interfaces.VALUE_TYPES_VOCABULARY, required=False)
	
class ImappingAttrGroup(IAttrGroup):
	lowerBound = FloatAttribute(title='The lower bound for the result of mapping a container', required=False)
	upperBound = FloatAttribute(title='The upper bound for the result of mapping a container', required=False)
	defaultValue = FloatAttribute(title='The default value from the target set', required=False, default=0)

class ImappingEntryAttrGroup(IAttrGroup):
	mapKey = ObjectAttribute(title=u'The source value', required=True)
	mappedValue = FloatAttribute(title='The mapped value', required=True)
	caseSensitive = BoolAttribute(title='Used to control whether or not a mapEntry string is matched case sensitively', required=True)

class IcorrectResponseAttrGroup(IAttrGroup):
	interpretation = TextLineAttribute(title=u'A human readable interpretation of the correct value', required=False)
	
class IareaMappingAttrGroup(IAttrGroup):
	lowerBound = FloatAttribute(title='The lower bound for the result of mapping a container', required=False)
	upperBound = FloatAttribute(title='The upper bound for the result of mapping a container', required=False)
	defaultValue = FloatAttribute(title='The default value from the target set', required=False, default=0)

class IareaMapEntryAttrGroup(IAttrGroup):
	shape = ChoiceAttribute(title="The shape of the area", vocabulary=qt_interfaces.SHAPE_TYPES_VOCABULARY, required=True)
	coords = TextLineAttribute(title='The size and position of the area', required=True)
	mappedValue = FloatAttribute(title='The mapped value', required=True)
	
class IoutcomeDeclarationAttrGroup(IAttrGroup):
	view = ChoiceAttribute(title='The intended audience for an outcome variable', vocabulary=qt_interfaces.VIEW_TYPES_VOCABULARY, required=False)
	interpretation = TextLineAttribute(title=u'A human readable interpretation of the variable value', required=False)
	longInterpretation = URIAttribute(title=u'An optional link to an extended interpretation', required=False)
	normalMaximum = FloatAttribute(title='Defines the maximum magnitude of numeric outcome variables', required=False)
	normalMinimum = FloatAttribute(title='Defines the minimum value of numeric outcome variables', required=False)
	masteryValue = FloatAttribute(title='Defines the mastery value of numeric outcome variables', required=False)
	
class IlookupTableAttrGroup(IAttrGroup):
	defaultValue = ObjectAttribute(title='The default outcome value to be used when no matching tabel entry is found', required=False, default=0)
	
class ImatchTableEntryAttrGroup(IAttrGroup):
	sourceValue = IntAttribute(title='The source integer that must be matched exactly', required=True)
	targetValue = ObjectAttribute(title=u'The target value that is used to set the outcome when a match is found.', required=True)

class IinterpolationTableEntryAttrGroup(IAttrGroup):
	sourceValue = FloatAttribute(title='The lower bound for the source value to match this entry', required=True)
	includeBoundary = BoolAttribute(title='Determines if an exact match of sourceValue matches this entry', required=False, default=True)
	targetValue = ObjectAttribute(title='The target value that is used to set the outcome when a match is found', required=True)
	
# content

class IflowAttrGroup(IAttrGroup):
	base = URIAttribute(title=u'The uri base', required=False)
	
class IobjectAttrGroup(IAttrGroup):
	data =  URIAttribute(title='Provides a URI for locating the data associated with the object', required=True)
	type =  MimeTypeAttribute(title='The mimetype',required=True)
	width =  IntAttribute(title='The width', required=False)
	length =  IntAttribute(title='The length', required=False)

class IparamAttrGroup(IAttrGroup):
	name =  TextLineAttribute(title='The name of the parameter, as interpreted by the object', required=True)
	value =  TextLineAttribute(title='The value to pass to the object',required=True)
	valuetype = ChoiceAttribute(title="The param type", vocabulary=qt_interfaces.PARAM_TYPES_VOCABULARY)
	type =  MimeTypeAttribute(title='The mimetype',required=False)

class IqAttrGroup(IAttrGroup):
	cite = URIAttribute(title=u'Citation URI', required=False)

class IblockquoteAttrGroup(IAttrGroup):
	cite = URIAttribute(title=u'Citation URI', required=False)
	
class IcolAttrGroup(IAttrGroup):
	span = IntAttribute(title=u'The col span', required=False)

class IcolgroupAttrGroup(IAttrGroup):
	span = IntAttribute(title=u'The col span', required=False)
	
class ItableAttrGroup(IAttrGroup):
	summary = TextLineAttribute(title=u'The table summary', required=False)
	
class ItableCellAttrGroup(IAttrGroup):
	headers = ListAttribute(title='Specifies one or more header cells a cell is related to', required=False,
							value_type=schema.TextLine(title='the header'))
	scope = ChoiceAttribute(title="The param type", vocabulary=qt_interfaces.SCOPE_TABLE_TYPES, required=False)
	abbr = TextLineAttribute(title='Abbreviated version', required=False)
	axis = TextLineAttribute(title='Categorizes header cells', required=False)
	rowspan = IntAttribute(title='Specifies the number of rows a header cell should span', required=False)
	colspan = IntAttribute(title='Specifies the number of cols a header cell should span', required=False)

class IimgAttrGroup(IAttrGroup):
	src = URIAttribute(title='Image URI', required=True)
	alt = TextLineAttribute(title="The param type", max_length=256, required=False)
	longdesc = URIAttribute(title='Image URI', required=False)
	height = IntAttribute(title='Image heigth', required=False)
	width = IntAttribute(title='Image width', required=False)
	
class IaAttrGroup(IAttrGroup):
	href = URIAttribute(title='href URI', required=True)
	type = TextLineAttribute(title="The mimeType", required=False)
	
class IFeedbackAttrGroup(IAttrGroup):
	outcomeIdentifier = TextLineAttribute(title="The identifier of an outcome", required=True)
	showHide = ChoiceAttribute(title="The visibility of the feedbackElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = TextLineAttribute(title="The identifier that determines the visibility of the feedback " +
								   "in conjunction with the showHide", required=True)
	
class IviewAttrGroup(IAttrGroup):
	view = TextLineAttribute(title="The views in which the rubric block's content are to be shown.", required=True)
	
class IstylesheetAttrGroup(IAttrGroup):
	href = URIAttribute(title='The identifier or location of the external stylesheet', required=True)
	type = MimeTypeAttribute(title="The mimeType", required=True)
	media = TextLineAttribute(title="An optional media descriptor", required=False)
	title = TextLineAttribute(title="An optional title for the stylesheet", required=False)

# interaction

class IinteractionAttrGroup(IAttrGroup):
	responseIdentifier = TextLineAttribute(title=u'The response identifier', required=True)
	
class IendAttemptInteractionAttrGroup(IAttrGroup):
	title = TextLineAttribute(title="The string that should be displayed to the candidate as a prompt for ending the attempt using this interaction", required=True)
	
class IinlineChoiceInteractionAttrGroup(IAttrGroup):
	shuffle = BoolAttribute(title="If the shuffle attribute is true then the delivery engine must randomize the order in which the choices are " +
							"presented subject to the fixed attribute.", required=True)
	
	required = BoolAttribute(title="If true then a choice must be selected by the candidate in order to form a valid response to the interaction", required=False)
	
class IpromptAttrGroup(IbodyElementAttrGroup):
	pass
	
class IchoiceAttrGroup(IbodyElementAttrGroup):
	identifier = TextLineAttribute(title=u'The element identifier', required=True)
	fixed = BoolAttribute(title=u'Fixed choice attribute', required=False)
	templateIdentifier = TextLineAttribute(title=u'The template identifier', required=False)
	showHide = ChoiceAttribute(title="Determines how the visibility of the choice is controlled", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=False)

class IsimpleChoiceAttrGroup(IchoiceAttrGroup):
	pass

class IassociableChoiceAttrGroup(IAttrGroup):
	matchGroup = ListAttribute(	title=u'A set of choices that this choice may be associated with, all others are excluded', required=False,
								value_type=schema.TextLine('the match group'))
	
class IchoiceInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True, default=1)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False, default=0)

class IassociateInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxAssociations = IntAttribute(title=u'Max associations allowed', required=True)
	minAssociations = IntAttribute(title=u'Min associations allowed', required=False)

class IsimpleAssociableChoiceAttrGroup(IAttrGroup):
	matchMax = IntAttribute(title=u'The maximum number of choices this choice may be associated', required=True)
	matchMin = IntAttribute(title=u'The minimum number of choices this choice must be associated', required=False, default=0)

class IorderInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxChoices = IntAttribute(title=u'Max choices allowed', required=False)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False)
	orientation = ChoiceAttribute(title="Determines how the visibility of the choice is controlled",
								  vocabulary=qt_interfaces.ORIENTATION_TYPES_VOCABULARY, required=False)
	
class ImatchInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	maxAssociations = IntAttribute(title=u'The maximum number of associations', required=True, default=1)
	minAssociations = IntAttribute(title=u'The minimum number of associations', required=False, default=0)

class IgapMatchInteractionAttrGroup(IAttrGroup):
	shufle = BoolAttribute(title=u'Shufle flag', required=True, default=False)
	
class IgapChoiceAttrGroup(IAttrGroup):
	matchMax = IntAttribute(title=u'The maximum number of choices this choice may be associated with', required=True)
	matchMin = IntAttribute(title=u'The minimum number of choices this choice may be associated with', required=False, default=0)
	
class IgapImgAttrGroup(IAttrGroup):
	objectLabel = TextLineAttribute(title=u'An optional label for the image object to be inserted', required=False)
	
class IgapAttrGroup(IAttrGroup):
	required = BoolAttribute(title=u'f true then this gap must be filled', required=False, default=False)
	
class IstringInteractionAttrGroup(IAttrGroup):
	base = IntAttribute(title=u'The number base', required=False)
	stringIdentifier = TextLineAttribute(title=u'The actual string entered by the candidate', required=False)
	expectedLength = IntAttribute(title=u'The hint to the expected length', required=False)
	patternMask = TextLineAttribute(title=u'The regular expression that the candidate must match', required=False)
	placeholderText = TextLineAttribute(title=u'Some placeholder text that can be used to vocalize the interactionh', required=False)

class IextendedTextInteractionAttrGroup(IAttrGroup):
	maxStrings = IntAttribute(title=u'The maximum number of separate strings accepted', required=False)
	minStrings = IntAttribute(title=u'The minimum number of separate strings accepted', required=False)
	expectedLines  = IntAttribute(title=u'The expected number of lines of input required.', required=False)
	format = ChoiceAttribute(title="The format of the tex",
							 vocabulary=qt_interfaces.TEXT_FORMAT_TYPES_VOCABULARY, required=False)

class IhottextInteractionAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'Max choices allowed', required=True, default=1)
	minChoices = IntAttribute(title=u'Min choices allowed', required=False, default=0)

class IhotspotAttrGroup(IAttrGroup):
	shape = ChoiceAttribute(title="The shape of the hotspot",
							 vocabulary=qt_interfaces.SHAPE_TYPES_VOCABULARY, required=True) 
	coords = TextLineAttribute(title="The size and position of the hotspot, interpreted in conjunction with the shape",required=True) 
	hotspotLabel = TextLineAttribute(title="The alternative text for this (hot) area of the image",required=False, max_length=256) 

class IassociableHotspotAttrGroup(IAttrGroup):
	matchMax = IntAttribute(title=u'The maximum number of choices this choice may be associated with', required=True)
	matchMin = IntAttribute(title=u'The minimum number of choices this choice may be associated with', required=False, default=0)
	
class IhotspotInteractiontAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'The maximum number of points that the candidate is allowed to select', required=True)
	minChoices = IntAttribute(title=u'The minimum number of points that the candidate is allowed to select', required=False, default=0)

class IselectPointInteractionAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'The maximum number of points that the candidate is allowed to select', required=True)
	minChoices = IntAttribute(title=u'The minimum number of points that the candidate is allowed to select', required=False, default=0)
		
class IgraphicOrderInteractiontAttrGroup(IAttrGroup):
	maxChoices = IntAttribute(title=u'The maximum number of choices to form a valid response to the interaction', required=False)
	minChoices = IntAttribute(title=u'The minimum number of choices to form a valid response to the interaction', required=False)

class IgraphicAssociateInteractiontAttrGroup(IAttrGroup):
	maxAssociations = IntAttribute(title=u'The maximum number of associations that the candidate is allowed to make', required=False, default=1)
	minAssociations = IntAttribute(title=u'The minimum number of associations that the candidate is required to make', required=False, default=0)
	
class IpositionObjectInteractiontAttrGroup(IAttrGroup):
	centerPoint = ListAttribute(title=u'Defines the point on the image being positioned', required=False, max_length=2, min_length=0,
								value_type=schema.Int(title='the value'))
	maxChoices = IntAttribute(title=u'The maximum number of points that the candidate is allowed to select', required=True)
	minChoices = IntAttribute(title=u'The minimum number of points that the candidate is allowed to select', required=False, default=0)

class IsliderInteractionAttrGroup(IAttrGroup):
	lowerBound = FloatAttribute(title="The lower bound", required=True)
	upperBound = FloatAttribute(title="The upper bound", required=True)
	step = IntAttribute(title="The steps that the control moves in", required=False)
	stepLabel = BoolAttribute(title="If the slider should be labeled", required=False, default=False)
	orientation = ChoiceAttribute(title="Hit to the rendering system",
								  vocabulary=qt_interfaces.ORIENTATION_TYPES_VOCABULARY, required=False)
	reverse = BoolAttribute(title="Reverse flag", required=False)
	
class ImediaInteractionAttrGroup(IAttrGroup):
	autostart = BoolAttribute(title="If the media object should begin as soon as it is presented", required=True)
	minPlays = IntAttribute(title="The minimum number of play times", required=False, default=0)
	maxPlays = IntAttribute(title="The maxumun number of play times", required=False, default=0)
	loop = BoolAttribute(title="The continuous play mode", required=False, default=False)

class IuploadInteractionAttrGroup(IAttrGroup):
	type = MimeTypeAttribute(title="The expected mime-type of the uploaded file", required=False)
	
class IitemBodyAttrGroup(IbodyElementAttrGroup):
	pass

class IassessmentItemAttrGroup(IAttrGroup):
	identifier = TextLineAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
