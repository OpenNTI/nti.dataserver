#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import component
from zope import interface

__all__ = ['MimeTypeDecorator']

from nti.externalization.interfaces import StandardExternalFields
CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE

from nti.externalization.singleton import SingletonDecorator
from nti.externalization import interfaces as ext_interfaces

from .mimetype import nti_mimetype_from_object

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(object)
class MimeTypeDecorator(object):
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, orig, result ):
		if CLASS in result and MIMETYPE not in result:
			mime_type = nti_mimetype_from_object( orig, 0 )
			if mime_type:
				result[MIMETYPE] = mime_type
