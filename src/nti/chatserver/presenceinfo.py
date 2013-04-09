#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the presence-related objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface
from zope import component
from . import interfaces as chat_interfaces
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.schema import PermissiveSchemaConfigured as SchemaConfigured
from nti.utils.schema import createDirectFieldProperties
from nti.utils.property import alias

from nti.mimetype.mimetype import nti_mimetype_with_class


@interface.implementer(chat_interfaces.IPresenceInfo)
class PresenceInfo(SchemaConfigured): # NOT persistent
	createDirectFieldProperties(chat_interfaces.IPresenceInfo)
	createDirectFieldProperties(nti_interfaces.ILastModified)
	createdTime = alias('lastModified') # overwrite

	__external_can_create__ = True
	mimeType = nti_mimetype_with_class( 'presenceinfo' )

	def __init__( self, *args, **kwargs ):
		self.lastModified = time.time()
		super(PresenceInfo,self).__init__( *args, **kwargs )

	def isAvailable(self):
		return self.type == 'available'


from nti.externalization.datastructures import InterfaceObjectIO

@component.adapter(chat_interfaces.IPresenceInfo)
class PresenceInfoInternalObjectIO(InterfaceObjectIO):
	"""We are different in that we allow setting Last Modified from the external object. This is because
	we tend to store this object in its JSON form in redis and would like to maintain that info."""
	_ext_iface_upper_bound = chat_interfaces.IPresenceInfo

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(PresenceInfoInternalObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )
		if 'Last Modified' in parsed:
			self._ext_self.lastModified = parsed['Last Modified']
