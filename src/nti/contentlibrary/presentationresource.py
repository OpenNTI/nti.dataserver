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

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties
from nti.schema.schema import EqHash

from nti.dublincore.interfaces import ILastModified
from nti.dublincore.time_mixins import DCTimesLastModifiedMixin

from nti.utils.property import CachedProperty

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

	root = None
	createDirectFieldProperties(IDisplayablePlatformPresentationResources)

	@property
	def createdTime(self):
		return self.root.createdTime

	@property
	def lastModified(self):
		return self.root.lastModified


class DisplayableContentMixin(object):
	"""
	A mixin for a :class:`.IDelimitedHierarchyEntry` that implements
	the presentation resources iterable.
	"""

	root = None

	@CachedProperty('root')
	def PlatformPresentationResources(self):
		# If the root is not yet filled in (None), then
		# the resulting AttributeError can get interpreted by hasattr()
		# as a missing attribute...and SchemaConfigured would try
		# to copy in the default value, which would overwrite
		# our CachedProperty. Thus we have to be defensive.
		root = getattr(self, 'root', None)
		if not root:
			return ()

		assets = root.getChildNamed('presentation-assets')
		if assets is None or not IDelimitedHierarchyBucket.providedBy(assets):
			return ()

		inherit = None
		data = list()

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
		return tuple(result)
