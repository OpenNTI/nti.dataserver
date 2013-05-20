# -*- coding: utf-8 -*-
"""
Defines QTI preconditions interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema

from .. import interfaces as qti_interfaces
from ..expression import interfaces as exp_interfaces
from ..attributes import interfaces as attr_interfaces

class IpreCondition(qti_interfaces.IConcrete):
	"""
	A preCondition is a simple expression attached to an assessmentSection or assessmentItemRef that must evaluate to true if the item is to be presented
	"""
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)

class IbranchRule(attr_interfaces.IbranchRuleAttrGroup, qti_interfaces.IConcrete):
	"""
	A branch-rule is a simple expression attached to an assessmentItemRef, assessmentSection or testPart that is evaluated after the item
	"""
	expression = schema.Object(exp_interfaces.Iexpression, title="The expression", required=True)
