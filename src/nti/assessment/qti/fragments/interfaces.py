from __future__ import unicode_literals, print_function, absolute_import

from zope import schema

from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.outcome import interfaces as out_interfaces
from nti.assessment.qti.response import interfaces as rsp_interfaces
from nti.assessment.qti.assessments import interfaces as ast_interfaces

class Iinclude(	cnt_interfaces.IblockStatic, cnt_interfaces.IflowStatic, cnt_interfaces.IinlineStatic, 
				out_interfaces.IoutcomeRule, rsp_interfaces.IresponseRule, ast_interfaces.IsectionPart, 
				qti_interfaces.IConcrete):
	pass

class IresponseProcessingFragment(rsp_interfaces.IresponseRule, qti_interfaces.IConcrete):
	responseRule = schema.List(schema.Object(rsp_interfaces.IresponseRule), min_length=0, title="Ordered list of response rules")

class IoutcomeProcessingFragment(out_interfaces.IoutcomeRule, qti_interfaces.IConcrete):
	outcomeRule = schema.List(schema.Object(out_interfaces.IoutcomeRule), min_length=0, title="Ordered list of outcome rules")

