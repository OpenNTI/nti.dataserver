#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces representing the indexed data that can be
attached to content units.


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.interfaces import ILocation
from nti.dublincore.interfaces import ILastModified



class IIndexedDataContainer(ILocation, ILastModified):
	"""
	The indexed data for a content unit. Because content units
	are not always persistent, this should not hold a direct reference
	to the content unit.

	These are expected to be accessed by adapting the content
	unit to this interface; there may be several different
	kinds or namespaces of indexed data associated with a
	content unit, in which case they would be named adapters.

	The actual contents of the indexed data items are not defined;
	however, they are required to be identified by ``ntiid``, and are
	typically represented as dictionaries.
	"""

	ntiid = interface.Attribute("The NTIID of the content unit.")

	def get_data_items():
		"""
		Return an iterable across the data items associated with
		this container in this namespace.
		"""

	def contains_data_item_with_ntiid(ntiid):
		"""
		Does this container (content unit) have data for the given
		ntiid?
		"""
		### XXX: JAM: Do these NTIIDs show up in the embeddedContainerNTIIDs
		# property of the content unit? They probably should...

class IWritableIndexedDataContainer(IIndexedDataContainer):
	"""
	For updating/writing the data container.
	"""

	def set_data_items(data_items):
		"""
		Make this container hold the given sequence of data items.
		"""

TAG_NAMESPACE_FILE = 'nti.contentlibrary.indexed_data.NamespaceFile'

class IAudioIndexedDataContainer(IWritableIndexedDataContainer):
	"""
	Special adapter, pre-namespaced for audio index data.
	"""

IAudioIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
										  'audio_index.json')

class IVideoIndexedDataContainer(IWritableIndexedDataContainer):
	"""
	Special adapter, pre-namespaced for video index data.
	"""

IVideoIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
										  'video_index.json')

class IRelatedContentIndexedDataContainer(IWritableIndexedDataContainer):
	"""
	Special adapter, pre-namespaced for related content index data.
	"""

IRelatedContentIndexedDataContainer.setTaggedValue(TAG_NAMESPACE_FILE,
												   'related_content_index.json')
