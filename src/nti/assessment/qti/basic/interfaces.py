from __future__ import unicode_literals, print_function

from zope import interface

from nti.assessment.qti.attributes import interfaces as attr_interfaces

class IbodyElement(attr_interfaces.IbodyElementAttrGroup):
	"""
	Marker interface for common attribute for elements
	"""
		
class ITextOrVariable(interface.Interface):
	pass
