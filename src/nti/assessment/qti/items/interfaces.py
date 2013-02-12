# -*- coding: utf-8 -*-
"""
Defines QTI items interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema

from ..qti import interfaces as qti_interfaces
from ..content import interfaces as cnt_interfaces
from ..response import interfaces as rsp_interfaces
from ..template import interfaces as tmp_interfaces
from ..feedback import interfaces as feed_interfaces
from ..variables import interfaces as var_interfaces
from ..attributes import interfaces as attr_interfaces

class IitemSessionControl(attr_interfaces.IitemSessionControlAttrGroup, qti_interfaces.IConcrete):
	pass

class IassessmentItem(attr_interfaces.IassessmentItemAttrGroup, qti_interfaces.IConcrete):
	responseDeclaration = schema.List(schema.Object(var_interfaces.IresponseDeclaration), min_length=0, required=True)
	outcomeDeclaration = schema.List(schema.Object(var_interfaces.IoutcomeDeclaration), min_length=0, required=True)
	templateDeclaration = schema.List(schema.Object(tmp_interfaces.ItemplateDeclaration), min_length=0, required=True)
	templateProcessing = schema.Object(tmp_interfaces.ItemplateProcessing, required=False)
	stylesheet = schema.List(schema.Object(cnt_interfaces.Istylesheet), min_length=0, title='Ordered list', required=False)
	itemBody = schema.Object(cnt_interfaces.IitemBody, required=False)
	responseProcessing  = schema.Object(rsp_interfaces.IresponseProcessing, required=False)
	modalFeedback = schema.List(schema.Object(feed_interfaces.ImodalFeedback), min_length=0, title='Ordered list', required=False)
