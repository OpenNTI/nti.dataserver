#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic implementations of IContentUnit functions

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.container.contained import Contained

from .interfaces import IContentUnit
from .interfaces import IContentPackage
from .interfaces import IPotentialLegacyCourseConflatedContentPackage
from .interfaces import IDisplayableContent
from .interfaces import ILegacyCourseConflatedContentPackage

from .presentationresource import DisplayableContentMixin

from nti.utils.property import alias

from nti.schema.schema import PermissiveSchemaConfigured
from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.dublincore.time_mixins import DCTimesLastModifiedMixin

@interface.implementer(IContentUnit)
class ContentUnit(PermissiveSchemaConfigured,
				  Contained,
				  DCTimesLastModifiedMixin):
	"""
	Simple implementation of :class:`IContentUnit`.
	"""
	# Note that we don't inherit from CreatedAndModifiedTimeMixin,
	# our subclasses have complicated rules for getting those values.
	# We simply provide initial defaults.

	__external_class_name__ = 'ContentUnit'

	createdTime = -1
	lastModified = -1

	createFieldProperties(IContentUnit)

	# These things need to override the field properties
	# XXX: JAM: This isn't really correct. The __name__ needs to be unique
	# within the container, but that isn't guaranteed for the title (?)
	# Unit-test failures can often be found if __name__ is allowed
	# to be a field property; those should be changed to title...
	# __name__ is commented out because the one test failure we saw has
	# been fixed
	#__name__ = alias('title')
	label = alias('title')

	def __repr__(self):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, getattr(self, 'key', self.href))


@interface.implementer(IPotentialLegacyCourseConflatedContentPackage)
class ContentPackage(ContentUnit,
					 DisplayableContentMixin):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	__external_class_name__ = 'ContentPackage'

	index_last_modified = -1

	createFieldProperties(IDisplayableContent,
						  # Omit PPR because of the mixin; otherwise we would override the mixin
						  omit=('PlatformPresentationResources'))
	createDirectFieldProperties(IContentPackage)
	createDirectFieldProperties(IPotentialLegacyCourseConflatedContentPackage)

	# IDCExtendedProperties.
	# Note that we're overriding these to provide
	# default values, thus losing the FieldProperty
	# implementation
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''


	# Legacy course support,
	# ALL DEPRECATED
	createDirectFieldProperties(ILegacyCourseConflatedContentPackage)

	#: A tuple of things thrown by the implementation's
	#: IO methods that represent transient states that may
	#: clear up by themself
	TRANSIENT_EXCEPTIONS = ()


# TODO: We need to do caching of does_sibling_entry_exist and read_contents.
# does_exist is used by appserver/censor_policies on every object creation/edit
# which quickly adds up.
# Right now, our policy for does_exist is a very simple, very dumb cache that we share
# with all content units, caching questions for 10 minutes.
# read_contents is not cached
import repoze.lru
_exist_cache = repoze.lru.ExpiringLRUCache(100000, default_timeout=600)  # this one is big because each entry is small
_content_cache = repoze.lru.ExpiringLRUCache(1000, default_timeout=600)  # this one is smaller because each entry is bigger

def _clear_caches():
	_exist_cache.clear()
	_content_cache.clear()

import zope.testing.cleanup
zope.testing.cleanup.addCleanUp(_clear_caches)
