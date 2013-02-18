# -*- coding: utf-8 -*-
"""
Defines interfaces for QTI element [XML] attributes

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from .. import interfaces as qt_interfaces
from ..schema import (TextLineAttribute, BoolAttribute, IntAttribute, URIAttribute,
					  ChoiceAttribute, MimeTypeAttribute, ListAttribute, FloatAttribute,
					  IntegerOrVariableRefAttribute, FloatOrVariableRefAttribute,
					  StringOrVariableRefAttribute, IdentifierRefAttribute)
	
class IAttrGroup(interface.Interface):
	pass

# basic

class IbodyElementAttrGroup(IAttrGroup):
	id = TextLineAttribute(title=u'The element id', required=False)
	klass = TextLineAttribute(title=u'The class', required=False, __name__='class')
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2, default='en')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	
# items

class IitemSessionControlAttrGroup(IAttrGroup):
	maxAttempts = IntAttribute(title=u'The maximum number of attempts allowed', required=False)
	showFeedback = BoolAttribute(title=u'This constraint affects the visibility of feedback after the end of the last attempt', required=False)
	allowReview = BoolAttribute(title=u'If set to true the item session is allowed to enter the review state during which the candidate can review the itemBody along with the responses they gave', required=False)
	showSolution = BoolAttribute(title=u'Show solution flag', required=False, default=False)
	allowComment = BoolAttribute(title=u'Support the capture of candidate comments', required=False)
	allowSkipping = BoolAttribute(title=u'An item is defined to be skipped if the candidate has not provided any response', required=False, default=True)
	validateResponses = BoolAttribute(title=u'Validate any response', required=False, default=True)

# variables

class IvalueAttrGroup(IAttrGroup):
	fieldIdentifier = IdentifierRefAttribute(title=u'The field id', required=False)
	baseType = ChoiceAttribute(title="The base-type", vocabulary=qt_interfaces.VALUE_TYPES_VOCABULARY, required=False)
	
class IdefaultValueAttrGroup(IAttrGroup):
	interpretation = TextLineAttribute(title=u'A human readable interpretation of the default value', required=False)
	
class IvalueDeclarationAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The id', required=True)
	cardinality = ChoiceAttribute(title="The variable cardinality", vocabulary=qt_interfaces.CARDINALITY_TYPES_VOCABULARY, required=True)
	baseType = ChoiceAttribute(title="The base-type", vocabulary=qt_interfaces.VALUE_TYPES_VOCABULARY, required=False)
	
class ImappingAttrGroup(IAttrGroup):
	lowerBound = FloatAttribute(title='The lower bound for the result of mapping a container', required=False)
	upperBound = FloatAttribute(title='The upper bound for the result of mapping a container', required=False)
	defaultValue = FloatAttribute(title='The default value from the target set', required=False, default=0.0)

class ImappingEntryAttrGroup(IAttrGroup):
	mapKey = TextLineAttribute(interface.Interface,title=u'The source value', required=True)
	mappedValue = FloatAttribute(title='The mapped value', required=True)
	caseSensitive = BoolAttribute(title='Used to control whether or not a mapEntry string is matched case sensitively', required=True)

class IcorrectResponseAttrGroup(IAttrGroup):
	interpretation = TextLineAttribute(title=u'A human readable interpretation of the correct value', required=False)
	
class IareaMappingAttrGroup(IAttrGroup):
	lowerBound = FloatAttribute(title='The lower bound for the result of mapping a container', required=False)
	upperBound = FloatAttribute(title='The upper bound for the result of mapping a container', required=False)
	defaultValue = FloatAttribute(title='The default value from the target set', required=False, default=0.0)

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
	defaultValue = TextLineAttribute(title='The default outcome value to be used when no matching tabel entry is found', required=False)
	
class ImatchTableEntryAttrGroup(IAttrGroup):
	sourceValue = IntAttribute(title='The source integer that must be matched exactly', required=True)
	targetValue = TextLineAttribute(interface.Interface, title=u'The target value that is used to set the outcome when a match is found.', required=True)

class IinterpolationTableEntryAttrGroup(IAttrGroup):
	sourceValue = FloatAttribute(title='The lower bound for the source value to match this entry', required=True)
	includeBoundary = BoolAttribute(title='Determines if an exact match of sourceValue matches this entry', required=False, default=True)
	targetValue = TextLineAttribute(interface.Interface, title='The target value that is used to set the outcome when a match is found', required=True)
	
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
	scope = ChoiceAttribute(title="The param type", vocabulary=qt_interfaces.SCOPE_TABLE_VOCABULARY, required=False)
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
	type = MimeTypeAttribute(title="The mimeType", required=False)
	
class IFeedbackAttrGroup(IAttrGroup):
	outcomeIdentifier = IdentifierRefAttribute(title="The identifier of an outcome", required=True)
	showHide = ChoiceAttribute(title="The visibility of the feedbackElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = IdentifierRefAttribute(title="The identifier that determines the visibility of the feedback " +
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
	responseIdentifier = IdentifierRefAttribute(title=u'The response identifier', required=True)
	
class IendAttemptInteractionAttrGroup(IAttrGroup):
	title = TextLineAttribute(title="The string that should be displayed to the candidate as a prompt for ending the attempt using this interaction", required=True)
	
class IinlineChoiceInteractionAttrGroup(IAttrGroup):
	shuffle = BoolAttribute(title="If the shuffle attribute is true then the delivery engine must randomize the order in which the choices are " +
							"presented subject to the fixed attribute.", required=True)
	
	required = BoolAttribute(title="If true then a choice must be selected by the candidate in order to form a valid response to the interaction", required=False)
	
class IpromptAttrGroup(IbodyElementAttrGroup):
	pass
	
class IchoiceAttrGroup(IbodyElementAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The element identifier', required=True)
	fixed = BoolAttribute(title=u'Fixed choice attribute', required=False)
	templateIdentifier = IdentifierRefAttribute(title=u'The template identifier', required=False)
	showHide = ChoiceAttribute(title="Determines how the visibility of the choice is controlled", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=False)

class IsimpleChoiceAttrGroup(IchoiceAttrGroup):
	pass

class IassociableChoiceAttrGroup(IAttrGroup):
	matchGroup = ListAttribute(	title=u'A set of choices that this choice may be associated with, all others are excluded', required=False,
								value_type=schema.TextLine(title='the match group'))
	
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
	stringIdentifier = IdentifierRefAttribute(title=u'The actual string entered by the candidate', required=False)
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

# response

class IresponseProcessingAttrGroup(IAttrGroup):
	template = URIAttribute(title="URI for responseProcessing template",required=False) 
	templateLocation = URIAttribute(title="responseProcessing template location",required=False) 

class IsetOutcomeValueAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The outcome variable to be set", required=True)
	
class IlookupOutcomeValueAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The outcome variable to be set", required=True)
	
# template

class ItemplateDeclarationAttrGroup(IAttrGroup):
	paramVariable = BoolAttribute(title="The substituted flag", required=False, default=False)
	mathVariable = BoolAttribute(title="The substituted flag in MathML expressions", required=False, default=False)

class ItemplateElementAttrGroup(IAttrGroup):
	showHide = ChoiceAttribute(title="The visibility of the templateElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = IdentifierRefAttribute(title="The identifier", required=True)

class IsetTemplateValueAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The identifier", required=True)
	
class IsetCorrectResponseAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The identifier", required=True)
	
class IsetDefaultValueAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The identifier", required=True)

# modalfeedback

class IImodalFeedbackAttrGroup(IAttrGroup):
	outcomeIdentifier = IdentifierRefAttribute(title="The outcome identifier", required=True)
	showHide = ChoiceAttribute(title="The visibility of the modelfeedbackElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = IdentifierRefAttribute(title="The identifier", required=True)
	title = TextLineAttribute(title="The title", required=False)

# assessment

class ItimeLimitsAttrGroup(IAttrGroup):
	minTime = IntAttribute(title='Min time measured in seconds', required=False)
	maxTime = IntAttribute(title='Max time measured in seconds', required=False)
	allowLateSubmission = BoolAttribute(title='Late submission flag', required=False)

class ItestPartAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The identifier of the test part", required=True)
	navigationMode = ChoiceAttribute(title="The navigation mode", vocabulary=qt_interfaces.NAVIGATION_MODE_VOCABULARY, required=True)
	submissionMode = ChoiceAttribute(title="The submission mode", vocabulary=qt_interfaces.SUBMISSION_MODE_VOCABULARY, required=True)
	
class IselectionAttrGroup(IAttrGroup):
	select = IntAttribute(title="The number of child elements to be selected", required=True)
	withReplacement = BoolAttribute(title="When selecting child elements each element is normally eligible for selection once only", required=False, default=False)
	
class IsectionPartAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="The identifier of the section part", required=True)
	required = BoolAttribute(title="If a child element is required it must appear (at least once) in the selection", required=True, default=False)
	fixed = BoolAttribute(title="If a child element is fixed it must never be shuffled", required=False, default=False)
	
class IorderingAttrGroup(IAttrGroup):
	shuffle = BoolAttribute(title="If true causes the order of the child elements to be randomized", required=False, default=False)

class IassessmentSectionAttrGroup(IAttrGroup):
	title = TextLineAttribute(title="The title", required=True)
	visible = BoolAttribute(title="A visible section is one that is identifiable by the candidate", required=True)
	keepTogether = BoolAttribute(title="Keep together flag", required=False, default=True)

class IassessmentSectionRefAttrGroup(IAttrGroup):
	href = URIAttribute(title="The uri is used to refer to the assessmentSection document file", required=True)
	
class IassessmentItemRefAttrGroup(IAttrGroup):
	href = URIAttribute(title="The uri is used to refer to the assessmentSection document file", required=True)
	category = ListAttribute(title='Items can optionally be assigned to one or more categories', required=False,
							 value_type=schema.TextLine(title='the category'))
	
class IweightAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title="An item can have any number of weights", required=True)
	value = IntAttribute(title="Weights are floating point values", required=True)
	
class IvariableMappingAttrGroup(IAttrGroup):
	sourceIdentifier = IdentifierRefAttribute(title="Source identifier", required=True)
	targetIdentifier = IdentifierRefAttribute(title="Target identifier", required=True)
	
class ItemplateDefaultAttrGroup(IAttrGroup):
	templateIdentifier = IdentifierRefAttribute(title="Template identifier", required=True)
	
class IassessmentTestAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The principle identifier of the test', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentTest', required=True)
	toolName = TextLineAttribute(title=u'The label', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
class IassessmentItemAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
# test-level feedback

class ItestFeedbackAttrGroup(IAttrGroup):
	access = ChoiceAttribute(title="Test feedback is shown to during the test or at the end of the testPart",
							 vocabulary=qt_interfaces.FEED_BACK_ACCESS_TYPES_VOCABULARY, required=True)
	outcomeIdentifier = IdentifierRefAttribute(title=u'The outcome identifier', required=True)
	showHide = ChoiceAttribute(title="The visibility of the feedbackElement", vocabulary=qt_interfaces.SHOW_HIDE_VOCABULARY, required=True)
	identifier = IdentifierRefAttribute(title=u'The identifier', required=True)
	title = TextLineAttribute(title=u'The title', required=False)
	
# pre-conditions and branching

class IbranchRuleAttrGroup(IAttrGroup):
	target = IdentifierRefAttribute(title=u'The identifier', required=True)

# expressions

class IbaseValueAttrGroup(IAttrGroup):
	baseType = ChoiceAttribute(title="The base-type of the value",vocabulary=qt_interfaces.BASE_TYPES_VOCABULARY, required=True)

class IvariableAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The variable identifier', required=True)
	weightIdentifier = IdentifierRefAttribute(title=u'An optional weighting to be applied to the value of the variable', required=False)

class IdefaultAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The identifier', required=True)
	
class IcorrectAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The identifier', required=True)
	
class ImapResponseAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The identifier', required=True)
	
class ImapResponsePointAttrGroup(IAttrGroup):
	identifier = IdentifierRefAttribute(title=u'The identifier', required=True)
	
class ImathConstantAttrGroup(IAttrGroup):
	name = ChoiceAttribute(title="Constant name", vocabulary=qt_interfaces.MATH_CONSTANTS_VOCABULARY, required=True)
	
class IrandomIntegerAttrGroup(IAttrGroup):
	min = IntegerOrVariableRefAttribute(title='Min int value or ref. template variable', required=True, default=0)
	max = IntegerOrVariableRefAttribute(title='Max int value or ref. template variable', required=True)
	step = IntegerOrVariableRefAttribute(title='Step int value or ref. template variable', required=False, default=1)

class IrandomFloatAttrGroup(IAttrGroup):
	min = FloatOrVariableRefAttribute(title='Min float value or ref. template variable', required=True, default=0)
	max = FloatOrVariableRefAttribute(title='Max float value or ref. template variable', required=True)
	
class IitemSubsetAttrGroup(IAttrGroup):
	sectionIdentifier = IdentifierRefAttribute(title='Section identifier', required=True)
	includeCategory = ListAttribute(title='If specified, only variables from items with a matching category are included', required=False,
							 		value_type=schema.TextLine(title='the category'))
	excludeCategory = ListAttribute(title='If specified, only variables from items with no matching category are included', required=False,
							 		value_type=schema.TextLine(title='the category'))
	
class ItestVariablesAttrGroup(IAttrGroup):
	variableIdentifier = IdentifierRefAttribute(title='Test variable identifier', required=True)
	baseType = ChoiceAttribute(title="The base-type of the value",vocabulary=qt_interfaces.BASE_TYPES_VOCABULARY, required=False)
	weightIdentifier = IdentifierRefAttribute(title='the defined weight is applied to each variable', required=False)
	
class IoutcomeMaximumAttrGroup(IAttrGroup):
	variableIdentifier = IdentifierRefAttribute(title='As per the variableIdentifier attribute of testVariables', required=True)
	weightIdentifier = IdentifierRefAttribute(title='As per the weightIdentifier attribute of testVariables', required=False)
	
class IoutcomeMinimumAttrGroup(IAttrGroup):
	variableIdentifier = IdentifierRefAttribute(title='As per the variableIdentifier attribute of testVariables', required=True)
	weightIdentifier = IdentifierRefAttribute(title='As per the weightIdentifier attribute of testVariables', required=False)
	
class IroundToAttrGroup(IAttrGroup):
	roundingMode = ChoiceAttribute(title="The rounding mode", vocabulary=qt_interfaces.ROUNDING_MODE_VOCABULARY, required=True)
	figures = IntegerOrVariableRefAttribute(title='The number of figures to round to', required=True)
	
class IstatsOperatorAttrGroup(IAttrGroup):
	name = ChoiceAttribute(title="The rounding mode", vocabulary=qt_interfaces.STAT_OPERATOR_NAMES_VOCABULARY, required=True)

class ImathOperatorAttrGroup(IAttrGroup):
	name = ChoiceAttribute(title="The math operator", vocabulary=qt_interfaces.MATH_OPERATORS_VOCABULARY, required=True)
		
class IrepeatAttrGroup(IAttrGroup):
	numberRepeats = IntegerOrVariableRefAttribute(title='The number of repeats', required=True)

class IindexAttrGroup(IAttrGroup):
	n = IntegerOrVariableRefAttribute(title='The index', required=True)
	
class IsubstringAttrGroup(IAttrGroup):
	caseSensitive= BoolAttribute(title='Used to control whether or not the substring is matched case sensitively', required=True, default=True)
	
class IfieldValueAttrGroup(IAttrGroup):
	fieldIdentifier = IdentifierRefAttribute(title='The identifier of the field to be selected', required=True)
	
class IanyNAttrGroup(IAttrGroup):
	min = IntegerOrVariableRefAttribute(title='The minimum number of sub-expressions that must be true', required=True)
	max = IntegerOrVariableRefAttribute(title='The maximum number of sub-expressions that may be true', required=True)
	
class IstringMatchAttrGroup(IAttrGroup):
	caseSensitive = BoolAttribute(title='Whether or not the match is to be carried out case sensitively', required=True)
	substring = BoolAttribute(title='Deprecated attribute', required=False, default=False)
	
class IpatternMatchAttrGroup(IAttrGroup):
	pattern = StringOrVariableRefAttribute(title='The syntax for the regular expression', required=True)
	
class IequalAttrGroup(IAttrGroup):
	toleranceMode = ChoiceAttribute(title="The tolerance mode", vocabulary=qt_interfaces.TOLERANCE_MODE_VOCABULARY, required=True)
	tolerance = ListAttribute(schema.Object(interface.Interface), title="The tolerance floatOrVariableRef", required=True, min_length=0, max_length=2)
	includeLowerBound = BoolAttribute(title=u'Controls whether or not the lower bound is included in the comparison', required=False, default=True)
	includeLowerBound = BoolAttribute(title=u'Controls whether or not the upper bound is included in the comparison', required=False, default=True)
	
class IequalRoundedAttrGroup(IAttrGroup):
	roundingMode = ChoiceAttribute(title="The tolerance mode", vocabulary=qt_interfaces.ROUNDING_MODE_VOCABULARY, required=True, default='significantFigures')
	figures = IntegerOrVariableRefAttribute(title='Numbers are rounded to a given number of significantFigures or decimalPlaces', required=True)
	
class IinsideAttrGroup(IAttrGroup):
	shape = ChoiceAttribute(title="The shape of the area", vocabulary=qt_interfaces.SHAPE_TYPES_VOCABULARY, required=True)
	coords = TextLineAttribute(title='The size and position of the area', required=True)

class IcustomOperatorAttrGroup(IAttrGroup):
	klass = TextLineAttribute(title="The class attribute allows simple sub-classes to be name", __name__='class', required=False)
	definition = URIAttribute(title='A URI that identifies the definition of the custom operator in the global namespace', required=False)
