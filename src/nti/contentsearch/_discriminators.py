# -*- coding: utf-8 -*-
"""
Discriminators functions

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from nti.contentprocessing import compute_ngrams

from nti.dataserver import interfaces as nti_interfaces

from ._content_utils import get_content
from . import interfaces as search_interfaces

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
	result = [x.lower() for x in result] if result else None
	return result or default

def get_sharedWith(obj, default=None):
	adapted = component.queryAdapter(obj, search_interfaces.IShareableContentResolver)
	result = adapted.get_flattenedSharingTargets() if adapted else ()
	result = [x.username for x in result if nti_interfaces.IEntity.providedBy(x)]
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

def get_replacement_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IRedactionContentResolver)
	result = get_content(adapted.get_replacement_content())
	return result.lower() if result else default
get_replacementContent = get_replacement_content

def get_redaction_explanation(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IRedactionContentResolver)
	result = get_content(adapted.get_redaction_explanation())
	return result.lower() if result else default
get_redactionExplanation = get_redaction_explanation

def get_post_title(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IPostContentResolver)
	result = get_content(adapted.get_title())
	return result.lower() if result else default

def get_post_title_and_ngrams(obj, default=None):
	title = get_post_title(obj, default)
	n_grams = compute_ngrams(title)
	result = '%s %s' % (title, n_grams) if title else None
	return result.lower() if result else default

def get_post_tags(obj, default=()):
	adapted = component.getAdapter(obj, search_interfaces.IPostContentResolver)
	result = adapted.get_tags() or default
	return result

def get_object_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = get_content(adapted.get_content())
	return result.lower() if result else default

def get_object_ngrams(obj, default=None):
	content = get_object_content(obj, default)
	n_grams = compute_ngrams(content) if content else default
	return n_grams if n_grams else default

def get_content_and_ngrams(obj, default=None):
	content = get_object_content(obj)
	n_grams = compute_ngrams(content)
	result = '%s %s' % (content, n_grams) if content else u''
	return result or default
