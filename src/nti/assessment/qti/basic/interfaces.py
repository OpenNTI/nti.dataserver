# -*- coding: utf-8 -*-
"""
Defines basic QTI element interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from nti.assessment.qti import interfaces as qti_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class IbodyElement(attr_interfaces.IbodyElementAttrGroup, qti_interfaces.IQTIElement):
	"""
	Marker interface for common attribute for elements
	"""
		
class ITextOrVariable(qti_interfaces.IQTIElement):
	pass
