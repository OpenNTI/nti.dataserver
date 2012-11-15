from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
from datetime import date

from zope import interface

from zope.index.field import FieldIndex

from zope.catalog.field import IFieldIndex
from zope.catalog.attribute import AttributeIndex

from zope.container.contained import Contained

from nti.chatserver import interfaces as chat_interfaces

import logging
logger = logging.getLogger(__name__)

@interface.implementer(IFieldIndex)
class _NormalizingFieldIndex(FieldIndex, Contained):
	def normalize( self, value ):
		return value

	def index_doc(self, docid, value):
		super(_NormalizingFieldIndex,self).index_doc( docid, self.normalize(value) )

	def apply( self, query ):
		return super(_NormalizingFieldIndex,self).apply( tuple([self.normalize(x) for x in query]) )
	
class _FieldIndex(AttributeIndex, _NormalizingFieldIndex):
	pass

class CreatorIndex(_FieldIndex):
	default_field_name = 'creator'
	default_interface = chat_interfaces.IMeeting
	
	def normalize( self, value ):
		if not isinstance(value, six.string_types):
			value = getattr(value, 'username')
		value = value.lower() if value else None
		return value
	
class RoomIdIndex(_FieldIndex):
	default_field_name = 'RoomId'
	default_interface = chat_interfaces.IMeeting

class ModeratedIndex(_FieldIndex):
	default_field_name = 'Moderated'
	default_interface = chat_interfaces.IMeeting
	
class CreatedDateIndex(_FieldIndex):
	default_field_name = 'CreatedTime'
	default_interface = chat_interfaces.IMeeting
	
	def normalize( self, value ):
		if isinstance(value, (int,float)):
			dt = date.fromtimestamp(value)
			return dt.isoformat()
		else:
			return value


