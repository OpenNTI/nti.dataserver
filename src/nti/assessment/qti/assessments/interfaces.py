# -*- coding: utf-8 -*-
"""
QTI assesments

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema

from .. import schema as qti_schema
from .. import interfaces as qti_interfaces
from ..content import interfaces as cnt_interfaces
from ..outcome import interfaces as out_interfaces
from ..items import interfaces as items_interfaces
from ..feedback import interfaces as fbck_interfaces
from ..variables import interfaces as var_interfaces
from ..expression import interfaces as exp_interfaces
from ..attributes import interfaces as attr_interfaces
from ..preconditions import interfaces as pre_interfaces

class Iselection(attr_interfaces.IselectionAttrGroup, qti_interfaces.IConcrete):
	pass
	
class Iordering(attr_interfaces.IorderingAttrGroup, qti_interfaces.IConcrete):
	pass

class ItimeLimits(attr_interfaces.ItimeLimitsAttrGroup, qti_interfaces.IConcrete):
	pass
	
class IvariableMapping(attr_interfaces.IvariableMappingAttrGroup, qti_interfaces.IConcrete):
	pass

class ItemplateDefault(qti_interfaces.IConcrete):
	expression = schema.Object(exp_interfaces.Iexpression , title="An expression", required=True)

class Iweight(attr_interfaces.IweightAttrGroup, qti_interfaces.IConcrete):
	pass
	
class IsectionPart(attr_interfaces.IsectionPartAttrGroup):
	preCondition = qti_schema.List(schema.Object(pre_interfaces.IpreCondition), title="An optional ordered set of conditions evaluated during the test", min_length=0)
	branchRule = qti_schema.List(schema.Object(pre_interfaces.IbranchRule), title="An optional ordered set of rules evaluated during the test", min_length=0)
	itemSessionControl = schema.Object(items_interfaces.IitemSessionControl, title="Parameters used to control the allowable states of each item session in this part", required=False)
	timeLimits = schema.Object(ItimeLimits, title="Optionally controls the amount of time a candidate is allowed for this part of the test", required=False)

class IassessmentSection(attr_interfaces.IassessmentSectionAttrGroup, IsectionPart, qti_interfaces.IConcrete):
	selection = schema.Object(Iselection, title="The rules used to select which children of the section are to be used for each instance of the test", required=False)
	ordering = schema.Object(Iordering, title="The rules used to determine the order in which the children of the section are to be arranged", required=False)
	rubricBlock = qti_schema.List(schema.Object(cnt_interfaces.IrubricBlock), title="Section rubric is presented to the candidate with each item contained by the section", min_length=0)
	sectionPart = qti_schema.List(schema.Object(IsectionPart), title="The ordered list of section parts", min_length=0)

class IassessmentSectionRef(attr_interfaces.IassessmentSectionRefAttrGroup, IsectionPart, qti_interfaces.IConcrete):
	pass

class IassessmentItemRef(attr_interfaces.IassessmentItemRefAttrGroup, IsectionPart, qti_interfaces.IConcrete):
	variableMapping = qti_schema.List(schema.Object(IvariableMapping), title="Variable mappings are used to alter the name of an item outcome for the purposes of this test", min_length=0)
	weight = qti_schema.List(schema.Object(Iweight), title="Weights allow custom values to be defined for scaling an item's outcomes", min_length=0)
	templateDefault = qti_schema.List(schema.Object(ItemplateDefault), title="WA template default is used to alter the default value", min_length=0)
	
class ItestPart(attr_interfaces.ItimeLimitsAttrGroup, qti_interfaces.IConcrete):
	preCondition = qti_schema.List(schema.Object(pre_interfaces.IpreCondition), title="An optional ordered set of conditions evaluated during the test", min_length=0)
	branchRule = qti_schema.List(schema.Object(pre_interfaces.IbranchRule), title="An optional ordered set of rules evaluated during the test", min_length=0)
	itemSessionControl = schema.Object(items_interfaces.IitemSessionControl, title="Parameters used to control the allowable states of each item session in this part", required=False)
	timeLimits = schema.Object(ItimeLimits, title="Optionally controls the amount of time a candidate is allowed for this part of the test.", required=False)
	assessmentSection = qti_schema.List(schema.Object(IassessmentSection), title="The items contained in each testPart are arranged into sections and sub-sections", min_length=1)
	testFeedback = qti_schema.List(schema.Object(fbck_interfaces.ItestFeedback), title="Test-level feedback specific to this part of the test", min_length=0)

class IassessmentTest(attr_interfaces.IassessmentTestAttrGroup, qti_interfaces.IConcrete):
	outcomeDeclaration = qti_schema.List(schema.Object(var_interfaces.IoutcomeDeclaration), title="Each test has an associated set of outcomes", min_length=0)
	timeLimits = schema.Object(ItimeLimits, title="Optionally controls the amount of time a candidate is allowed for the entire test", required=False)
	testPart = qti_schema.List(schema.Object(ItestPart), title="Order list of test parts (sections, sub-sections and so on)", min_length=1)
	outcomeProcessing = schema.Object(out_interfaces.IoutcomeProcessing, title="The set of rules used for calculating the values of the test outcomes", required=False)
	testFeedback = qti_schema.List(schema.Object(fbck_interfaces.ItestFeedback), title="The ordered test-level feedback controlled by the test outcomes.", min_length=0)
