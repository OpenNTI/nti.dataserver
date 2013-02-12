# -*- coding: utf-8 -*-
"""
Defines QTI variables interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope.interface.common.sequence import IFiniteSequence

from ..qti import interfaces as qti_interfaces
from ..basic import interfaces as basic_interfaces
from ..attributes import interfaces as attr_interfaces

class Ivalue(attr_interfaces.IvalueAttrGroup, qti_interfaces.IConcrete):
	pass

class IdefaultValue(attr_interfaces.IdefaultValueAttrGroup, IFiniteSequence, qti_interfaces.IConcrete):
	value = schema.List(schema.Object(Ivalue), title="An ordered list of values", min_length=1)

class IvariableDeclaration(basic_interfaces.IbodyElement, attr_interfaces.IvalueDeclarationAttrGroup):
	defaultValue = schema.Object(IdefaultValue, title="An optional default value for the variable", required=False)

class ImapEntry(attr_interfaces.ImappingEntryAttrGroup, qti_interfaces.IConcrete):
	pass
	
class Imapping(attr_interfaces.ImappingAttrGroup, IFiniteSequence, qti_interfaces.IConcrete):
	mapEntry = schema.List(schema.Object(ImapEntry), title="The map is defined by a set of mapEntries", min_length=1)
	
# response variables

class IareaMapEntry(attr_interfaces.IareaMapEntryAttrGroup, qti_interfaces.IConcrete):
	pass
	
class IareaMapping(attr_interfaces.IareaMappingAttrGroup, IFiniteSequence, qti_interfaces.IConcrete):
	areaMapEntry = schema.List(schema.Object(IareaMapEntry), title="An ordered list of entries", min_length=1)
	
class IcorrectResponse(attr_interfaces.IcorrectResponseAttrGroup, IFiniteSequence, qti_interfaces.IConcrete):
	value = schema.List(schema.Object(Ivalue), title="An ordered list of values", min_length=1)
	
class IresponseDeclaration(IvariableDeclaration, qti_interfaces.IConcrete):
	correctResponse = schema.Object(IcorrectResponse, title="May indicate the only possible value of the response variable", required=False)
	mapping = schema.Object(Imapping, title="Response mapping", required=False)
	areaMapping = schema.Object(IareaMapping, title="Provides an alternative form of mapping", required=False)
	
# outcome variables

class IlookupTable(attr_interfaces.IlookupTableAttrGroup):
	pass
	
class ImatchTableEntry(attr_interfaces.ImatchTableEntryAttrGroup, qti_interfaces.IConcrete):
	pass
	
class ImatchTable(IlookupTable, IFiniteSequence, qti_interfaces.IConcrete):
	matchTableEntry = schema.List(schema.Object(ImatchTableEntry), title="An ordered list of entries", min_length=1)

class IinterpolationTableEntry(attr_interfaces.IinterpolationTableEntryAttrGroup, qti_interfaces.IConcrete):
	pass
	
class IinterpolationTable(IlookupTable, IFiniteSequence, qti_interfaces.IConcrete):
	interpolationTableEntry = schema.List(schema.Object(IinterpolationTableEntry), title="An ordered list of entries", min_length=1)
	
class IoutcomeDeclaration(IvariableDeclaration, IFiniteSequence, attr_interfaces.IoutcomeDeclarationAttrGroup, qti_interfaces.IConcrete):
	lookupTable = schema.Object(IlookupTable, title="The lookup table", required=False)
	
