#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.deprecation import deprecated

from persistent import Persistent

from persistent.mapping import PersistentMapping

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

deprecated('_RepozeEntityIndexManager', 'No longer used')
class _RepozeEntityIndexManager(PersistentMapping):
	pass

deprecated('IndexManager', 'No longer used')
class IndexManager(object):
	pass

deprecated('BookContent', 'No longer used')
class BookContent(object):
	pass

deprecated('VideoTranscriptContent', 'No longer used')
class VideoTranscriptContent(object):
	pass

deprecated('AudioTranscriptContent', 'No longer used')
class AudioTranscriptContent(object):
	pass

deprecated('NTICardContent', 'No longer used')
class NTICardContent(object):
	pass

deprecated('create_index_manager', 'No longer used')
def create_index_manager(*args, **kwargs):
	return None

deprecated('get_sharedWith', 'No longer used')
def get_sharedWith(*args, **kwargs):
	return ()

deprecated('get_object_ngrams', 'No longer used')
def get_object_ngrams(*args, **kwargs):
	return ()

deprecated('get_object_content', 'No longer used')
def get_object_content(*args, **kwargs):
	return None

deprecated('WhooshContentSearcher', 'No longer used')
class WhooshContentSearcher(PersistentCreatedAndModifiedTimeObject):
	pass
	
deprecated('IndexStorage', 'No longer used')
class IndexStorage(Persistent):
	pass

deprecated('DirectoryStorage', 'No longer used')
class DirectoryStorage(Persistent):
	pass
