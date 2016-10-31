#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from six import string_types

from zope import component

from zope.intid import IIntIds

from nti.common.string import safestr

from nti.contentprocessing import compute_ngrams
from nti.contentprocessing.interfaces import IStopWords

from nti.externalization.oids import to_external_ntiid_oid

from .content_utils import tokenize_content

from .interfaces import IACLResolver
from .interfaces import ITagsResolver
from .interfaces import ITypeResolver
from .interfaces import ITitleResolver
from .interfaces import INTIIDResolver
from .interfaces import IContentResolver
from .interfaces import ICreatorResolver
from .interfaces import IKeywordsResolver
from .interfaces import IContainerIDResolver
from .interfaces import ICreatedTimeResolver
from .interfaces import INoteContentResolver
from .interfaces import ILastModifiedResolver
from .interfaces import IRedactionContentResolver
from .interfaces import IShareableContentResolver
from .interfaces import IMessageInfoContentResolver

def get_content(text, lang='en'):
	__traceback_info__ = text
	try:
		text = safestr(text)
		tokens = tokenize_content(text, lang)
	except ValueError:
		logger.exception('Cannot tokenize "%s"', text)
		tokens = [text]
	# remove stop words
	sw_util = component.queryUtility(IStopWords)
	stopwords = sw_util.stopwords(lang) if sw_util is not None else ()
	if stopwords:
		result = ' '.join(x for x in tokens if x.lower() not in stopwords)
	else:
		result = ' '.join(tokens)
	return unicode(result)

def get_oid(obj):
	result = to_external_ntiid_oid(obj)
	return result

def get_uid(obj, intids=None):
	intids = component.getUtility(IIntIds) if intids is None else intids
	result = intids.getId(obj)
	return result

def query_uid(obj, intids=None):
	intids = component.queryUtility(IIntIds) if intids is None else intids
	result = intids.queryId(obj) if intids is not None else None
	return result

def get_object(uid, intids=None):
	intids = component.getUtility(IIntIds) if intids is None else intids
	result = intids.getObject(int(uid))
	return result

def query_object(uid, default=None, intids=None):
	intids = component.queryUtility(IIntIds) if intids is None else intids
	result = intids.queryObject(int(uid), default) if intids is not None else None
	return result

def get_type(obj, default=None):
	adapted = ITypeResolver(obj, None)
	result = adapted.type if adapted else None
	return result or default

def get_mimetype(obj, default=None):
	result = getattr(obj, 'mimeType', None) or getattr(obj, 'mime_type', None)
	return result or default

def get_containerId(obj, default=None):
	adapted = IContainerIDResolver(obj, None)
	result = adapted.containerId if adapted else None
	return result or default

def get_ntiid(obj, default=None):
	adapted = INTIIDResolver(obj, None)
	result = adapted.ntiid if adapted else None
	return result or default

def get_creator(obj, default=None):
	adapted = ICreatorResolver(obj, None)
	result = adapted.creator if adapted else None
	return result or default

def get_title(obj, default=None, language='en'):
	adapted = ITitleResolver(obj, None)
	result = get_content(adapted.title, language) if adapted else None
	return result.lower() if result else default

def get_ngrams(value, language='en', default=None):
	try:
		result = compute_ngrams(value, language)
	except ValueError:
		logger.exception('Cannot compute ngrams "%s"', value)
		result = default
	return result

def _as_value_and_ngrams(value, default=None, lower=True, language='en'):
	value_is_string = isinstance(value, string_types)
	value_is_nonempty_string = value_is_string and bool(value)

	if value_is_nonempty_string:
		n_grams = get_ngrams(value, language)
		result = '%s %s' % (value, n_grams)
		if lower:
			result = result.lower()
	else:
		result = default
	return result

def get_title_and_ngrams(obj, default=None, language='en'):
	title = get_title(obj, default, language)
	return _as_value_and_ngrams(title, default, True, language)

def get_last_modified(obj, default=None):
	adapted = ILastModifiedResolver(obj, None)
	result = adapted.lastModified if adapted else None
	return result if result else default

def get_created_time(obj, default=None):
	adapted = ICreatedTimeResolver(obj, None)
	result = adapted.createdTime if adapted else None
	return result if result else default

def get_tags(obj, default=()):
	result = set()
	for resolver in component.subscribers((obj,), ITagsResolver):
		result.update(resolver.tags or ())
	return list(result) if result else default

def get_keywords(obj, default=()):
	result = set()
	for resolver in component.subscribers((obj,), IKeywordsResolver):
		result.update(resolver.keywords or ())
	return list(result) if result else default

def get_sharedWith(obj, default=None):
	adapted = IShareableContentResolver(obj, None)
	result = adapted.sharedWith if adapted else None
	return result or default

def get_acl(obj, default=None):
	adapted = IACLResolver(obj, None)
	result = adapted.acl if adapted else None
	return result or default

def get_references(obj, default=None):
	adapted = INoteContentResolver(obj, None)
	result = adapted.references if adapted else None
	return result or default

def get_channel(obj, default=None):
	adapted = IMessageInfoContentResolver(obj, None)
	result = adapted.channel if adapted else None
	return result or default

def get_recipients(obj, default=None):
	adapted = IMessageInfoContentResolver(obj, None)
	result = adapted.recipients if adapted else None
	return result or default

def get_replacement_content(obj, default=None, language='en'):
	adapted = IRedactionContentResolver(obj, None)
	result = get_content(adapted.replacementContent, language) if adapted else None
	return result.lower() if result else default
get_replacementContent = get_replacement_content

def get_redaction_explanation(obj, default=None, language='en'):
	adapted = IRedactionContentResolver(obj, None)
	result = get_content(adapted.redactionExplanation, language) if adapted else None
	return result.lower() if result else default
get_redactionExplanation = get_redaction_explanation

def get_replacement_content_and_ngrams(obj, default=None, language='en'):
	result = get_replacement_content(obj, default, language)
	return _as_value_and_ngrams(result, default, False, language)

def get_redaction_explanation_and_ngrams(obj, default=None, language='en'):
	result = get_redaction_explanation(obj, default, language)
	return _as_value_and_ngrams(result, default, False, language)

get_note_title = get_title
get_note_title_and_ngrams = get_title_and_ngrams

get_post_tags = get_tags
get_post_title = get_title
get_post_title_and_ngrams = get_title_and_ngrams

def get_object_content(obj, default=None, language='en'):
	adapted = IContentResolver(obj, None)
	result = get_content(adapted.content, language) if adapted is not None else None
	return result.lower() if result else default

def get_object_ngrams(obj, default=None, language='en'):
	content = get_object_content(obj, default, language)
	if isinstance(content, string_types) and content:
		result = get_ngrams(content, language, default)
	else:
		result = default
	return result

def get_content_and_ngrams(obj, default=None, language='en'):
	content = get_object_content(obj, language)
	return _as_value_and_ngrams(content, default, False, language)
