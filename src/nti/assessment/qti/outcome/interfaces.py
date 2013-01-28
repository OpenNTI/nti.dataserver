from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces

class IoutcomeRule(interface.Interface):
	pass
	
class IoutcomeProcessing(interface.Interface, IFiniteSequence, basic_interfaces.IConcrete):
	IoutcomeRule = schema.List(schema.Object(IoutcomeRule), title="Order list of outcome rules", min_length=0)
	