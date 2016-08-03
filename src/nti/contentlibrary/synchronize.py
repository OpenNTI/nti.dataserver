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

from nti.externalization.representation import WithRepr

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ISynchronizationParams
from .interfaces import ISynchronizationResults
from .interfaces import IContentPackageSyncResults
from .interfaces import ILibrarySynchronizationResults

CONTENT_REMOVAL_ERROR_CODE 	 = 001
MISSING_NTIID_ERROR_CODE 	 = 010
DUPLICATE_PACAKGES_ERROR_CODE = 100
UNMATCHED_ROOT_NTTID_ERROR_CODE = 105
MISSING_PACAKGE_REFERENCE_ERROR_CODE = 110

class SynchronizationException(Exception):

	code = None

	def __str__(self, *args, **kwargs):
		result = Exception.__str__(self, *args, **kwargs)
		if self.code is not None:
			result += '. Code:%s' % self.code
		return  result

class ContentRemovalException(SynchronizationException):
	code = CONTENT_REMOVAL_ERROR_CODE

class MissingContentBundleNTIIDException(SynchronizationException):
	code = MISSING_NTIID_ERROR_CODE

class DuplicatePacakgeException(SynchronizationException):
	code = DUPLICATE_PACAKGES_ERROR_CODE

class UnmatchedRootNTIIDException(SynchronizationException):
	code = UNMATCHED_ROOT_NTTID_ERROR_CODE

class MissingContentPacakgeReferenceException(SynchronizationException):
	code = MISSING_PACAKGE_REFERENCE_ERROR_CODE

@WithRepr
@interface.implementer(ISynchronizationParams)
class SynchronizationParams(SchemaConfigured):
	createDirectFieldProperties(ISynchronizationParams)

	packages = alias('ntiids')
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

	def __getitem__(self, index):
		return self.Items[index]

	def __setitem__(self, index, value):
		self.Items[index] = value
	
	def __len__(self):
		return len(self.Items or ())

	def __iter__(self):
		return iter(self.Items or ())

	def add(self, item):
		assert item is not None
		self.Items = [] if self.Items is None else self.Items
		item.__parent__ = self
		self.Items.append(item)
	append = add

@WithRepr
@interface.implementer(IContentPackageSyncResults)
class ContentPackageSyncResults(SchemaConfigured, Contained):
	createDirectFieldProperties(IContentPackageSyncResults)

	SiteName = alias('Site')

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

	def add_assessment(self, item, locked=False):
		assert item is not None
		ntiid = getattr(item, 'ntiid', item)
		name = 'AssessmentsSyncLocked' if locked else 'AssessmentsUpdated'
		if getattr(self, name, None) is None:
			setattr(self, name, set())
		getattr(self, name).add(ntiid)

	def add_asset(self, item, locked=False):
		assert item is not None
		ntiid = getattr(item, 'ntiid', item)
		name = 'AssetsSyncLocked' if locked else 'AssetsUpdated'
		if getattr(self, name, None) is None:
			setattr(self, name, set())
		getattr(self, name).add(ntiid)
