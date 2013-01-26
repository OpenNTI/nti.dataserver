from __future__ import unicode_literals, print_function

from zope import interface

from nti.assessment.qti.attributes import interfaces as attr_interfaces

class IConcrete(interface.Interface):
	"""
	Marker interface for concreate QTI classes
	"""
	__display_name__ = interface.Attribute("Display name")

class IbodyElement(attr_interfaces.IbodyElementAttrGroup):
	"""
	Marker interface for common attribute for elements
	"""
		
class ITextOrVariable(interface.Interface):
	pass
