#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.location.interfaces import IContained

from plone.namedfile.file import NamedBlobFile

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from ..interfaces import INamedFile

@interface.implementer(INamedFile, IContained)
class NamedFile(PersistentCreatedModDateTrackingObject, # Order matters
				NamedBlobFile,
				SchemaConfigured):

	createDirectFieldProperties(INamedFile)
		
	name = None
	__parent__ = __name__ = None

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self, *args, **kwargs)
		
	def __str__(self):
		return "%s(%s)" % (self.__class__.__name__, self.filename)
	__repr__ = __str__
