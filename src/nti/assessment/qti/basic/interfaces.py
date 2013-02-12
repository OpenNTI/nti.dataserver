# -*- coding: utf-8 -*-
"""
Defines basic QTI element interfaces

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from ..attributes import interfaces as attr_interfaces

class IbodyElement(attr_interfaces.IbodyElementAttrGroup):
	"""
	Marker interface for common attribute for elements
	"""
		
class ITextOrVariable(interface.Interface):
	pass
