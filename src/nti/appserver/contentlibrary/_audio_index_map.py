#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the audio index  map and supporting
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

from nti.appserver.contentlibrary import interfaces as app_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

@interface.implementer(app_interfaces.IAudioIndexMap)
class AudioIndexMap(dict):

	def __init__(self):
		super(AudioIndexMap, self).__init__()
		self.by_container = {}  # {ntiid => [audio id]}

	def clear(self):
		super(AudioIndexMap, self).clear()
		self.by_container.clear()

@component.adapter(lib_interfaces.IContentPackage, lce_interfaces.IObjectAddedEvent)
def add_audio_items_from_new_content(content_package, event):
	audio_map = component.queryUtility(app_interfaces.IAudioIndexMap)
	if audio_map is None:  # pragma: no cover
		return

	logger.info("Adding audio items from new content %s %s", content_package, event)
	try:
		audio_index_text = content_package.read_contents_of_sibling_entry('audio_index.json')
		_populate_audio_map_from_text(audio_map, audio_index_text, content_package)
	except:
		logger.exception("Failed to load audio items, invalid audio_index for %s", content_package)

def _populate_audio_map_from_text(audio_map, audio_index_text, content_package):
	if not audio_index_text:
		return

	audio_index_text = unicode(audio_index_text, 'utf-8') \
	if isinstance(audio_index_text, six.binary_type) else audio_index_text

	index = simplejson.loads(audio_index_text)

	# add containers:
	containers = index.get('Containers', {})
	for k, v in containers.items():
		audio_map.by_container[k] = v

@component.adapter(lib_interfaces.IContentPackage, lce_interfaces.IObjectRemovedEvent)
def remove_audio_items_from_old_content(content_package, event):
	audio_map = component.queryUtility(app_interfaces.IAudioIndexMap)
	library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
	if audio_map is None or library is None:
		return

	logger.debug("Clearing audio items from old content %s %s", content_package, event)

	audios = audio_map.by_container.pop(content_package.ntiid, ())
	for vid in audios:
		audio_map.pop(vid, None)

	for unit in library.childrenOfNTIID(content_package.ntiid):
		audios = audio_map.by_container.pop(unit.ntiid, ())
		for vid in audios:
			audio_map.pop(vid, None)
