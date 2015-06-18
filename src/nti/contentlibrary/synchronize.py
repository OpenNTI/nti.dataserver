#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.contained import Contained

from nti.common.property import alias
from nti.common.representation import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ISynchronizationParams
from .interfaces import ISynchronizationResults
from .interfaces import ILibrarySynchronizationResults

MISSING_NTIID_ERROR_CODE = 010
DUPLICATE_PACAKGES_ERROR_CODE = 100
MISSING_PACAKGE_REFERENCE_ERROR_CODE = 110

class SynchronizationExeception(Exception):
	
	code = None
	
	def __str__(self, *args, **kwargs):
		result = Exception.__str__(self, *args, **kwargs)
		if self.code is not None:
			result += '. Code:%s' % self.code
		return  result

class MissingContentBundleNTIIDException(SynchronizationExeception):
	code = MISSING_NTIID_ERROR_CODE

class DuplicatePacakgeException(SynchronizationExeception):
	code = DUPLICATE_PACAKGES_ERROR_CODE

class MissingContentPacakgeReferenceException(SynchronizationExeception):
	code = MISSING_PACAKGE_REFERENCE_ERROR_CODE

@WithRepr
@interface.implementer(ISynchronizationParams)
class SynchronizationParams(SchemaConfigured):
	createDirectFieldProperties(ISynchronizationParams)

	allowDrops = alias('allowRemoval')

@WithRepr
@interface.implementer(ILibrarySynchronizationResults)
class LibrarySynchronizationResults(SchemaConfigured, Contained):
	createDirectFieldProperties(ILibrarySynchronizationResults)

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

	def added(self, ntiid):
		self.Added = [] if self.Added is None else self.Added
		self.Added.append(ntiid)

	def modified(self, ntiid):
		self.Modified = [] if self.Modified is None else self.Modified
		self.Modified.append(ntiid)
	updated = modified

	def removed(self, ntiid):
		self.Removed = [] if self.Removed is None else self.Removed
		self.Removed.append(ntiid)
	dropped = removed

@WithRepr
@interface.implementer(ISynchronizationResults)
class SynchronizationResults(SchemaConfigured, Contained):
	createDirectFieldProperties(ISynchronizationResults)

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

	def add(self, item):
		assert item is not None
		self.Items = [] if self.Items is None else self.Items
		item.__parent__ = self
		self.Items.append(item)
	append = add
