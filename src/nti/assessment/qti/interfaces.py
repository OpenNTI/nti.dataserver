from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface

from nti.assessment.qti.schema import BoolAttribute
from nti.assessment.qti.schema import TextLineAttribute

class IItemBody(interface.Interface):
	"""
	Describe the item's content and information
	"""
	__display_name__ = 'itemBody'
	
	
class IAssessmentItem(interface.Interface):
	"""
	Encompasses the information that is presented to a candidate and information about how to score the item.
	"""
	
	__display_name__ = 'assessmentItem'
	
	identifier = TextLineAttribute(title=u'The principle identifier of the item', required=True)
	title = TextLineAttribute(title=u'The title of an assessmentItem', required=True, default=u'')
	label = TextLineAttribute(title=u'The label', required=False, max_length=256)
	lang = TextLineAttribute(title=u'The language code (RFC3066)', required=False, max_length=2)
	adaptive = BoolAttribute(title=u'Items are classified into Adaptive Items and Non-adaptive Items', required=True, default=False)
	timeDependent = BoolAttribute(title=u'If item is time dependent', required=True, default=False)
	toolName = TextLineAttribute(title=u'The tool id name', required=False, max_length=256)
	toolVersion = TextLineAttribute(title=u'The tool version', required=False, max_length=256)
	
	itemBody = schema.Object(IItemBody, title='The item body', required=False)