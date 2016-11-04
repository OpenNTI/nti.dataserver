#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Home of presentation resources.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.coremetadata.interfaces import ILastModified

from nti.dublincore.time_mixins import DCTimesLastModifiedMixin

from nti.property.property import CachedProperty

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from .interfaces import IDelimitedHierarchyBucket
from .interfaces import IDisplayablePlatformPresentationResources

@interface.implementer(IDisplayablePlatformPresentationResources,
					   ILastModified)
@EqHash('root')
class DisplayablePlatformPresentationResources(DCTimesLastModifiedMixin,
											   SchemaConfigured):

	"""
	Basic implementation of presentation resources.
	"""

	__external_can_create__ = False

	createDirectFieldProperties(IDisplayablePlatformPresentationResources)

	root = None

	@property
	def createdTime(self):
		return self.root.createdTime

	@property
	def lastModified(self):
		return self.root.lastModified

def get_platform_resentation_resources(root=None):
	if not root:
		return ()

	assets = root.getChildNamed('presentation-assets')
	if assets is None or not IDelimitedHierarchyBucket.providedBy(assets):
		return ()

	data = list()
	inherit = None
	for platform_bucket in assets.enumerateChildren():

		if not IDelimitedHierarchyBucket.providedBy(platform_bucket):
			continue

		if platform_bucket.name == 'shared':
			inherit = platform_bucket.name

		for version_bucket in platform_bucket.enumerateChildren():
			if 	not IDelimitedHierarchyBucket.providedBy(version_bucket) \
				or not version_bucket.name.startswith('v'):
				continue
			version = int(version_bucket.name[1:])
			data.append( (platform_bucket, version_bucket, version) )

	result = list()
	for x in data:
		ip_name = 'shared' if inherit and x[0].name != 'shared' else None
		dr = DisplayablePlatformPresentationResources(PlatformName=x[0].name,
													  root=x[1],
													  Version=x[2],
													  InheritPlatformName=ip_name)
		result.append(dr)
	result = tuple(result)
	return result

class DisplayableContentMixin(object):
	"""
	A mixin for a :class:`.IDelimitedHierarchyEntry` that implements
	the presentation resources iterable.
	"""

	root = None

	@classmethod
	def get_platform_resentation_resources(self, root=None):
		result = get_platform_resentation_resources(root)
		return result

	@property
	def _v_root(self):
		# If the root is not yet filled in (None), then
		# the resulting AttributeError can get interpreted by hasattr()
		# as a missing attribute...and SchemaConfigured would try
		# to copy in the default value, which would overwrite
		# our CachedProperty. Thus we have to be defensive.
		root = getattr(self, 'root', None)
		return root

	@property
	def _v_rootLastModified(self):
		result = getattr(self._v_root, 'lastModified', 0)
		return result

	@CachedProperty('root', '_v_rootLastModified')
	def _v_PlatformPresentationResources(self):
		result = get_platform_resentation_resources(self._v_root)
		return result

	@CachedProperty('root')
	def PlatformPresentationResources(self):
		result = get_platform_resentation_resources(self._v_root)
		return result
