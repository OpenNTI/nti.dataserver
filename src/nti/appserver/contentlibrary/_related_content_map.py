#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the related content index map and supporting
functions to maintain it.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import simplejson

from zope import interface
from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from . import CommonIndexMap
from . import interfaces as app_interfaces

@interface.implementer(app_interfaces.IRelatedContentIndexMap)
class RelatedContentIndexMap(CommonIndexMap):
	pass

@component.adapter(lib_interfaces.IContentPackage, lce_interfaces.IObjectAddedEvent)
def add_related_content_items_from_new_content(content_package, event):
	rc_map = component.queryUtility(app_interfaces.IRelatedContentIndexMap)
	if rc_map is None:  # pragma: no cover
		rc_map

	logger.info("Adding related items from new content %s %s", content_package, event)

	try:
		index_text = content_package.read_contents_of_sibling_entry('related_content_index.json')
		_populate_rc_map_from_text(rc_map, index_text, content_package)
	except:
		logger.exception("Failed to load related content items, invalid cache index for %s", content_package)

def _populate_rc_map_from_text(rc_map, index_text, content_package):
	if not index_text:
		return

	video_index_text = unicode(index_text, 'utf-8') \
	if isinstance(index_text, six.binary_type) else index_text

	index = simplejson.loads(video_index_text)

	# add items
	items = index.get('Items') if 'Items' in index else index
	for k, v in items.items():
		rc_map[k] = v

	# add containers:
	containers = index.get('Containers', {})
	for k, v in containers.items():
		rc_map.by_container[k] = v

@component.adapter(lib_interfaces.IContentPackage, lce_interfaces.IObjectRemovedEvent)
def remove_related_content_items_from_old_content(content_package, event):
	rc_map = component.queryUtility(app_interfaces.IRelatedContentIndexMap)
	library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
	if rc_map is None or library is None:
		return

	logger.debug("Clearing related content items from old content %s %s", content_package, event)

	related_content = rc_map.by_container.pop(content_package.ntiid, ())
	for rcid in related_content:
		rc_map.pop(rcid, None)

	for unit in library.childrenOfNTIID(content_package.ntiid):
		related_content = rc_map.by_container.pop(unit.ntiid, ())
		for rcid in related_content:
			rc_map.pop(rcid, None)
