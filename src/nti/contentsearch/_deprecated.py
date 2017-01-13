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


deprecated('get_content', 'No longer used')
def get_content(*args, **kwargs):
    return None


deprecated('get_oid', 'No longer used')
def get_oid(*args, **kwargs):
    return None


deprecated('get_uid', 'No longer used')
def get_uid(*args, **kwargs):
    return None


deprecated('query_uid', 'No longer used')
def query_uid(*args, **kwargs):
    return None


deprecated('get_object', 'No longer used')
def get_object(*args, **kwargs):
    return None


deprecated('query_object', 'No longer used')
def query_object(*args, **kwargs):
    return None


deprecated('get_type', 'No longer used')
def get_type(*args, **kwargs):
    return None

deprecated('get_mimetype', 'No longer used')
def get_mimetype(*args, **kwargs):
    return None


deprecated('get_containerId', 'No longer used')
def get_containerId(*args, **kwargs):
    return None


deprecated('get_ntiid', 'No longer used')
def get_ntiid(*args, **kwargs):
    return None


deprecated('get_creator', 'No longer used')
def get_creator(*args, **kwargs):
    return None


deprecated('get_title', 'No longer used')
def get_title(*args, **kwargs):
    return None

deprecated('get_ngrams', 'No longer used')
def get_ngrams(*args, **kwargs):
    return None


deprecated('get_ngrams', 'No longer used')
def get_title_and_ngrams(*args, **kwargs):
    return ()


deprecated('get_last_modified', 'No longer used')
def get_last_modified(*args, **kwargs):
    return 0

deprecated('get_created_time', 'No longer used')
def get_created_time(*args, **kwargs):
    return 0


deprecated('get_tags', 'No longer used')
def get_tags(*args, **kwargs):
    return ()


deprecated('get_keywords', 'No longer used')
def get_keywords(*args, **kwargs):
    return ()


deprecated('get_acl', 'No longer used')
def get_acl(*args, **kwargs):
    return None


deprecated('get_references', 'No longer used')
def get_references(*args, **kwargs):
    return None


deprecated('get_channel', 'No longer used')
def get_channel(*args, **kwargs):
    return None


deprecated('get_recipients', 'No longer used')
def get_recipients(*args, **kwargs):
    return None


deprecated('get_replacement_content', 'No longer used')
def get_replacement_content(*args, **kwargs):
    return None
get_replacementContent = get_replacement_content


deprecated('get_redaction_explanation', 'No longer used')
def get_redaction_explanation(*args, **kwargs):
    return None
get_redactionExplanation = get_redaction_explanation


deprecated('get_replacement_content_and_ngrams', 'No longer used')
def get_replacement_content_and_ngrams(*args, **kwargs):
    return None


deprecated('get_redaction_explanation_and_ngrams', 'No longer used')
def get_redaction_explanation_and_ngrams(*args, **kwargs):
    return None

get_note_title = get_title
get_note_title_and_ngrams = get_title_and_ngrams

get_post_tags = get_tags
get_post_title = get_title
get_post_title_and_ngrams = get_title_and_ngrams


deprecated('get_content_and_ngrams', 'No longer used')
def get_content_and_ngrams(*args, **kwargs):
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
