#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the video index  map and supporting
functions to maintain it.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import simplejson

from zope import interface
from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from . import interfaces as app_interfaces

@interface.implementer(app_interfaces.IVideoIndexMap)
class VideoIndexMap(dict):

	def __init__(self):
		super(VideoIndexMap, self).__init__()
		self.by_container = {}  # {ntiid => [video id]}

	def clear(self):
		super(VideoIndexMap, self).clear()
		self.by_container.clear()

@component.adapter(lib_interfaces.IContentPackage, lce_interfaces.IObjectCreatedEvent)
def add_video_items_from_new_content(content_package, event):
	#### from IPython.core.debugger import Tracer; Tracer()()  ####
	video_map = component.getUtility(app_interfaces.IVideoIndexMap)
	if video_map is None:  # pragma: no cover
		return

	logger.debug("Adding video items from new content %s %s", content_package, event)

	try:
		video_index_text = content_package.read_contents_of_sibling_entry('video_index.json')
		_populate_video_map_from_text(video_map, video_index_text, content_package)
	except:
		logger.exception("Failed to load video items, invalid video_index for %s", content_package)

def _populate_video_map_from_text(video_map, video_index_text, content_package):
	if not video_index_text:
		return

	video_index_text = unicode(video_index_text, 'utf-8') if isinstance(video_index_text, six.binary_type) else video_index_text
	index = simplejson.loads(video_index_text)

	# add items
	items = index.get('Items') if 'Items' in index else index
	for k, _ in items.items():
		# TODO: eventually we will add NTIVideo object
		video_map[k] = None

	# add containers:
	containers = index.get('Containers', {})
	for k, v in containers.items():
		video_map.by_container[k] = v

@component.adapter(lib_interfaces.IContentPackage, lce_interfaces.IObjectRemovedEvent)
def remove_video_items_from_old_content(content_package, event):
	video_map = component.getUtility(app_interfaces.IVideoIndexMap)
	library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
	if video_map and library:  # pragma: no cover
		logger.debug("Clearing video items from old content %s %s", content_package, event)
		for unit in library.childrenOfNTIID(content_package.ntiid):
			videos = video_map.by_container.pop(unit.ntiid, ())
			for vid in videos:
				video_map.pop(vid)
