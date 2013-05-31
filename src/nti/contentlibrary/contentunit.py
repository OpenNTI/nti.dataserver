#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic implementations of IContentUnit functions

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.utils.property import alias
from nti.contentlibrary.interfaces import IContentUnit, IContentPackage

@interface.implementer(IContentUnit)
class ContentUnit(object):
	"""
	Simple implementation of :class:`IContentUnit`.
	"""

	__external_class_name__ = 'ContentUnit'

	ordinal = 1
	href = None
	key = None
	ntiid = None
	icon = None
	thumbnail = None

	# DCDescriptiveProperties
	title = None
	description = None


	children = ()
	embeddedContainerNTIIDs = ()
	__parent__ = None

	def __init__(self, **kwargs):
		for k, v in kwargs.items():
			__traceback_info__ = k, v
			if hasattr(self, k):
				setattr(self, k, v)
			else:  # pragma: no cover
				logger.warn("Ignoring unknown key %s = %s", k, v)

	__name__ = alias('title')
	label = alias('title')


	def __repr__(self):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, getattr(self, 'key', self.href))


@interface.implementer(IContentPackage)
class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	__external_class_name__ = 'ContentPackage'

	root = None
	index = None
	index_last_modified = None
	index_jsonp = None
	installable = False
	archive = None
	archive_unit = None
	renderVersion = 1

	# IDCExtended
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''
	description = ''

	# : A tuple of things thrown by the implementation's
	# : IO methods that represent transient states that may
	# : clear up by themself
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
