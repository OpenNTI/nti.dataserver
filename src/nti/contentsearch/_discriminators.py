# -*- coding: utf-8 -*-
"""
Discriminators functions

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.intid
from zope import component

from nti.contentprocessing import compute_ngrams

from ._content_utils import get_content
from . import interfaces as search_interfaces

def get_uid(obj, intids=None):
	intids = intids or component.getUtility(zope.intid.IIntIds)
	result = intids.getId(obj)
	return result

def query_uid(obj, intids=None):
	intids = intids or component.getUtility(zope.intid.IIntIds)
	result = intids.queryId(obj)
	return result

def get_object(uid, intids=None):
	intids = intids or component.getUtility(zope.intid.IIntIds)
	result = intids.getObject(int(uid))
	return result

def query_object(uid, default=None, intids=None):
	intids = intids or component.getUtility(zope.intid.IIntIds)
	result = intids.queryObject(int(uid), default)
	return result

def get_containerId(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContainerIDResolver)
	return adapted.get_containerId() or default

def get_ntiid(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.INTIIDResolver)
	return adapted.get_ntiid() or default

def get_creator(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.ICreatorResolver)
	return adapted.get_creator() or default

def get_last_modified(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.ILastModifiedResolver)
	result = adapted.get_last_modified()
	return result if result else default

def get_keywords(obj, default=()):
	adapted = component.queryAdapter(obj, search_interfaces.IThreadableContentResolver)
	result = adapted.get_keywords() if adapted else None
	return result or default

def get_sharedWith(obj, default=None):
	adapted = component.queryAdapter(obj, search_interfaces.IShareableContentResolver)
	result = adapted.get_sharedWith() if adapted else None
	return result or default

def get_references(obj, default=None):
	adapted = component.queryAdapter(obj, search_interfaces.INoteContentResolver)
	result = adapted.get_references() if adapted else None
	return result or default

def get_channel(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IMessageInfoContentResolver)
	return adapted.get_channel() or default

def get_recipients(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IMessageInfoContentResolver)
	result = adapted.get_recipients()
	return result or default

def get_replacement_content(obj, default=None, language='en'):
	adapted = component.getAdapter(obj, search_interfaces.IRedactionContentResolver)
	result = get_content(adapted.get_replacement_content(), language)
	return result.lower() if result else default
get_replacementContent = get_replacement_content

def get_redaction_explanation(obj, default=None, language='en'):
	adapted = component.getAdapter(obj, search_interfaces.IRedactionContentResolver)
	result = get_content(adapted.get_redaction_explanation(), language)
	return result.lower() if result else default
get_redactionExplanation = get_redaction_explanation

def get_replacement_content_and_ngrams(obj, default=None, language='en'):
	result = get_replacement_content(obj, default, language)
	ngrams = compute_ngrams(result, language)
	result = '%s %s' % (result, ngrams) if result else None
	return result or default

def get_redaction_explanation_and_ngrams(obj, default=None, language='en'):
	result = get_redaction_explanation(obj, default, language)
	ngrams = compute_ngrams(result, language)
	result = '%s %s' % (result, ngrams) if result else None
	return result or default

def get_post_title(obj, default=None, language='en'):
	adapted = component.getAdapter(obj, search_interfaces.IBlogContentResolver)
	result = get_content(adapted.get_title(), language)
	return result.lower() if result else default

def get_post_title_and_ngrams(obj, default=None, language='en'):
	title = get_post_title(obj, default, language)
	n_grams = compute_ngrams(title, language)
	result = '%s %s' % (title, n_grams) if title else None
	return result.lower() if result else default

def get_post_tags(obj, default=()):
	adapted = component.getAdapter(obj, search_interfaces.IBlogContentResolver)
	result = adapted.get_tags() or default
	return result

def get_object_content(obj, default=None, language='en'):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = get_content(adapted.get_content(), language)
	return result.lower() if result else default

def get_object_ngrams(obj, default=None, language='en'):
	content = get_object_content(obj, default, language)
	n_grams = compute_ngrams(content, language) if content else default
	return n_grams if n_grams else default

def get_content_and_ngrams(obj, default=None, language='en'):
	content = get_object_content(obj, language)
	n_grams = compute_ngrams(content, language)
	result = '%s %s' % (content, n_grams) if content else u''
	return result or default
