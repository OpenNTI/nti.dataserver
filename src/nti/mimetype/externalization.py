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

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization import interfaces as ext_interfaces

from nti.mimetype import mimetype

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(object)
class MimeTypeDecorator(object):

	def __init__( self, o ):
		pass

	def decorateExternalMapping( self, orig, result ):
		if StandardExternalFields.CLASS in result and StandardExternalFields.MIMETYPE not in result:
			mime_type = mimetype.nti_mimetype_from_object( orig, use_class=False )
			if mime_type:
				result[StandardExternalFields.MIMETYPE] = mime_type
