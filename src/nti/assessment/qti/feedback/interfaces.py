from __future__ import unicode_literals, print_function

from zope import schema
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.content import interfaces as cnt_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class ImodalFeedback(attr_interfaces.IImodalFeedbackAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	flowStatic = schema.List(schema.Object(cnt_interfaces.IflowStatic), title="An ordered list of values", min_length=0)

class ItestFeedback(attr_interfaces.ItestFeedbackAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	flowStatic = schema.List(schema.Object(cnt_interfaces.IflowStatic), title="An optional ordered set of conditions evaluated during the test", min_length=0)