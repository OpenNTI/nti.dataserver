from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from zope.catalog.field import FieldIndex
from zope.catalog.field import IFieldIndex

from zope.container.contained import Contained

from nti.chatserver import interfaces as chat_interfaces

import logging
logger = logging.getLogger(__name__)

@interface.implementer(IFieldIndex)
class _FieldIndex(FieldIndex, Contained):
	pass

class RoomIdIndex(_FieldIndex):
	default_field_name = 'RoomId'
	default_interface = chat_interfaces.IMeeting

class CreatedTimeIndex(_FieldIndex):
	default_field_name = 'CreatedTime'
	default_interface = chat_interfaces.IMeeting

class ModeratedIndex(_FieldIndex):
	default_field_name = 'Moderated'
	default_interface = chat_interfaces.IMeeting
