#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters to get indexed data for content units.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.annotation.interfaces import IAnnotations

from .container import IndexedDataContainer
from .container import AudioIndexedDataContainer
from .container import VideoIndexedDataContainer
from .container import RelatedContentIndexedDataContainer

_KEY =  'nti.contentlibrary.indexed_data.container.IndexedDataContainer'

def indexed_data_adapter(content_unit,
						 factory=IndexedDataContainer,
						 namespace=''):

	key = _KEY
	if namespace:
		key = key + '_' + namespace

	annotations = IAnnotations(content_unit)
	result = annotations.get(key)
	if result is None:
		result = annotations[key] = factory(content_unit.ntiid)

	return result

# TODO: The namespace data is duplicated in subscribers.py;
# a bit of meta-programming (and iface tagged data) could
# fix the duplication.

def audio_indexed_data_adapter(content_unit):
	return indexed_data_adapter(content_unit,
								factory=AudioIndexedDataContainer,
								namespace='audio_index.json')

def video_indexed_data_adapter(content_unit):
	return indexed_data_adapter(content_unit,
								factory=VideoIndexedDataContainer,
								namespace='video_index.json')

def related_content_indexed_data_adapter(content_unit):
	return indexed_data_adapter(content_unit,
								factory=RelatedContentIndexedDataContainer,
								namespace='related_content_index.json')
