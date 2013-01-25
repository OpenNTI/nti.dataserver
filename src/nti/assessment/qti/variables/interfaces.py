from __future__ import unicode_literals, print_function

from zope import schema
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class Ivalue(attr_interfaces.IvalueAttrGroup):
	__display_name__ = "value"
	pass

class IdefaultValue(attr_interfaces.IdefaultValueAttrGroup, IFiniteSequence):
	__display_name__ = "defaultValue"
	value = schema.List(Ivalue, title="An ordered list of values", min_length=1)

class IvariableDeclaration(qti_interfaces.IbodyElement, attr_interfaces.IvalueDeclarationAttrGroup):
	defaultValue = schema.Object(IdefaultValue, title="An optional default value for the variable", min_length=1)

class ImapEntry(attr_interfaces.ImappingEntryAttrGroup):
	__display_name__ = "mapEntry"
	
class Imapping(attr_interfaces.ImappingAttrGroup, IFiniteSequence):
	__display_name__ = "mapping"
	mapEntry = schema.List(ImapEntry, title="The map is defined by a set of mapEntries", min_length=1)
	
# response variables

class IareaMapEntry(attr_interfaces.IareaMapEntryAttrGroup):
	__display_name__ = "areaMapEntry"
	
class IareaMapping(attr_interfaces.IareaMappingAttrGroup, IFiniteSequence):
	__display_name__ = "areaMapping"
	areaMapEntry = schema.List(IareaMapEntry, title="An ordered list of entries", min_length=1)
	
class IcorrectResponse(attr_interfaces.IcorrectResponseAttrGroup, IFiniteSequence):
	__display_name__ = "correctResponse"
	value = schema.List(Ivalue, title="An ordered list of values", min_length=1)
	
class IresponseDeclaration(IvariableDeclaration):
	__display_name__ = "responseDeclaration"
	correctResponse = schema.Object(IcorrectResponse, title="May indicate the only possible value of the response variable", required=False)
	mapping = schema.Object(Imapping, title="Response mapping", required=False)
	areaMapping = schema.Object(IareaMapping, title="Provides an alternative form of mapping", required=False)
	
# outcome variables

class IlookupTable(attr_interfaces.IlookupTableAttrGroup):
	pass
	
class ImatchTableEntry(attr_interfaces.ImatchTableEntryAttrGroup):
	__display_name__ = "matchTableEntry"
	
class ImatchTable(IlookupTable, IFiniteSequence):
	__display_name__ = "matchTable"
	matchTableEntry = schema.List(ImatchTableEntry, title="An ordered list of entries", min_length=1)

class IinterpolationTableEntry(attr_interfaces.IinterpolationTableEntryAttrGroup):
	__display_name__ = "interpolationTableEntry"
	
class IinterpolationTable(IlookupTable, IFiniteSequence):
	__display_name__ = "interpolationTable"
	interpolationTableEntry  = schema.List(IinterpolationTableEntry , title="An ordered list of entries", min_length=1)
	
class IoutcomeDeclaration(IvariableDeclaration, IFiniteSequence, attr_interfaces.IoutcomeDeclarationAttrGroup):
	__display_name__ = "outcomeDeclaration"
	lookupTable = schema.Object(IlookupTable, title="The lookup table", required=False)
	
