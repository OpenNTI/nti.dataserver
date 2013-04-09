#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the presence-related objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from . import interfaces as chat_interfaces

from nti.utils.schema import PermissiveSchemaConfigured as SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from nti.mimetype.mimetype import nti_mimetype_with_class

@interface.implementer(chat_interfaces.IPresenceInfo)
class PresenceInfo(SchemaConfigured): # NOT persistent
	createDirectFieldProperties(chat_interfaces.IPresenceInfo)
	__external_can_create__ = True
	mimeType = nti_mimetype_with_class( 'presenceinfo' )



from nti.externalization.datastructures import InterfaceObjectIO

@component.adapter(chat_interfaces.IPresenceInfo)
class PresenceInfoInternalObjectIO(InterfaceObjectIO):
	_ext_iface_upper_bound = chat_interfaces.IPresenceInfo
