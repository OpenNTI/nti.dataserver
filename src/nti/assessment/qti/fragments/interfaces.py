# -*- coding: utf-8 -*-
"""
Defines QTI fragment interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema

from ..qti import interfaces as qti_interfaces
from ..content import interfaces as cnt_interfaces
from ..outcome import interfaces as out_interfaces
from ..response import interfaces as rsp_interfaces
from ..assessments import interfaces as ast_interfaces

class Iinclude(	cnt_interfaces.IblockStatic, cnt_interfaces.IflowStatic, cnt_interfaces.IinlineStatic, 
				out_interfaces.IoutcomeRule, rsp_interfaces.IresponseRule, ast_interfaces.IsectionPart, 
				qti_interfaces.IConcrete):
	pass

class IresponseProcessingFragment(rsp_interfaces.IresponseRule, qti_interfaces.IConcrete):
	responseRule = schema.List(schema.Object(rsp_interfaces.IresponseRule), min_length=0, title="Ordered list of response rules")

class IoutcomeProcessingFragment(out_interfaces.IoutcomeRule, qti_interfaces.IConcrete):
	outcomeRule = schema.List(schema.Object(out_interfaces.IoutcomeRule), min_length=0, title="Ordered list of outcome rules")

