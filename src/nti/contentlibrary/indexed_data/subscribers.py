#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subscribers to keep the index data up to date.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import anyjson as json

def _update_index_when_content_changes(content_package, namespace, index_iface):
	# We track the modification timestamp of the key, if it exists,
	# and compare it to the modification timestamp of the root unit, updating
	# everything when the root unit changes

	sibling_key = content_package.does_sibling_entry_exist(namespace)
	if not sibling_key:
		# Nothing to do
		return

	root_index_container = index_iface(content_package)
	if root_index_container.lastModified >= sibling_key.lastModified:
		# nothing to do
		return

	# Yay, something to do!
	root_index_container.updateLastMod(sibling_key.lastModified)
	index_text = content_package.read_contents_of_sibling_entry(namespace)

	if isinstance(index_text, bytes):
		index_text = index_text.decode('utf-8')

	index = json.loads(index_text)
	# These are structured as follows:
	# {
	#   Items: { ntiid-of_item: data }
	#   Containers: { ntiid-of-content-unit: [list-of-ntiid-of-item ] }
	# }
	# We have to clear/update every contained child,
	# so the simplest thing is to recurse.

	def set_contents(unit):
		container = index_iface(unit)
		container.updateLastMod(sibling_key.lastModified)

		data_items = list()
		# If any of these ids are missing, the index is corrupt
		__traceback_info__ = unit
		for indexed_id in index['Containers'].get(container.ntiid, ()):
			__traceback_info__ = unit, indexed_id
			data_items.append(index['Items'][indexed_id])

		container.set_data_items(data_items)

		for child in unit.children:
			set_contents(child)

	set_contents(content_package)

from .interfaces import IAudioIndexedDataContainer
from .interfaces import IRelatedContentIndexedDataContainer
from .interfaces import IVideoIndexedDataContainer

def _update_audio_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  'audio_index.json',
											  IAudioIndexedDataContainer)


def _update_video_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  'video_index.json',
											  IVideoIndexedDataContainer)


def _update_related_content_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  'related_content_index.json',
											  IRelatedContentIndexedDataContainer)
