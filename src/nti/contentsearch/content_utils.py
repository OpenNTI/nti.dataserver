# -*- coding: utf-8 -*-
"""
Search content utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import collections

from zope import component
from zope import interface

from dolmen.builtins import IDict

from nti.contentlibrary import interfaces as lib_interfaces

from nti.contentprocessing import split_content
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing import get_content_translation_table

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import CanvasTextShape
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from nti.externalization.oids import to_external_ntiid_oid

from nti.utils.maps import CaseInsensitiveDict

from . import common
from . import interfaces as search_interfaces

from .constants import (CLASS, BODY, ID, NTIID, CREATOR, CONTAINER_ID, AUTO_TAGS)
from .constants import (text_, body_, selectedText_, replacementContent_, redactionExplanation_,
					 	keywords_, tag_fields, last_modified_fields, sharedWith_,
					 	highlight_, note_, post_, tags_, messageinfo_, redaction_, canvas_,
					 	canvastextshape_, references_, title_, inReplyTo_, recipients_, channel_,
					 	flattenedSharingTargetNames_)

def get_ntiid_path(ntiid, library=None, registry=component):
	result = ()
	library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) if library is None else library
	if library and ntiid:
		paths = library.pathToNTIID(ntiid)
		result = tuple([p.ntiid for p in paths]) if paths else ()
	return result

def get_collection_root(ntiid, library=None, registry=component):
	library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) if library is None else library
	paths = library.pathToNTIID(ntiid) if library else None
	return paths[0] if paths else None

def get_collection_root_ntiid(ntiid, library=None, registry=component):
	croot = get_collection_root(ntiid, library, registry)
	result = croot.ntiid.lower() if croot else None
	return result

def get_content(text=None, language='en'):
	result = ()
	text = unicode(text) if text else None
	if text:
		table = get_content_translation_table(language)
		result = split_content(text.translate(table), language)
	result = ' '.join(result)
	return unicode(result)

def is_ngram_compatible(term, language='en'):
	tokens = split_content(term)
	__traceback_info__ = term, tokens
	ncomp = component.getUtility(cp_interfaces.INgramComputer, name=language)
	min_word = min(map(len, tokens)) if tokens else 0
	return min_word >= ncomp.minsiz

@interface.implementer(search_interfaces.IContentResolver)
@component.adapter(basestring)
class _StringContentResolver(object):

	def __init__(self, content):
		self.content = content

	def get_content(self):
		result = unicode(self.content) if self.content else None
		return result

def _process_words(words):
	if words:
		if isinstance(words, six.string_types):
			words = [unicode(w.lower()) for w in words.split()]
		elif isinstance(words, collections.Iterable):
			words = [unicode(w.lower()) for w in words]
		else:
			words = ()
	return words or ()

@interface.implementer(search_interfaces.IContentResolver)
class _BasicContentResolver(object):

	def __init__(self, obj):
		self.obj = obj

class _AbstractIndexDataResolver(_BasicContentResolver):

	def get_ntiid(self):
		result = to_external_ntiid_oid(self.obj)
		return result

	def get_creator(self):
		result = self.obj.creator
		if nti_interfaces.IEntity.providedBy(result):
			result = unicode(result.username)
		return unicode(result) if result else None

	def get_containerId(self):
		result = self.obj.containerId
		return unicode(result) if result else None

	def get_sharedWith(self):
		data = ()
		if nti_interfaces.IReadableShared.providedBy(self.obj):
			data = self.obj.flattenedSharingTargetNames
		result = _process_words(data)
		return result

	def get_flattenedSharingTargets(self):
		if nti_interfaces.IReadableShared.providedBy(self.obj):
			return self.obj.flattenedSharingTargets
		return ()

	def get_last_modified(self):
		result = self.obj.lastModified
		result = float(result) if result is not None else None
		return result

class _ThreadableContentResolver(_AbstractIndexDataResolver):

	def get_tags(self):
		result = set()
		for name in tag_fields:
			data = getattr(self.obj, name, ())
			result.update(_process_words(data))
		return list(result) if result else []

	def get_keywords(self):
		result = getattr(self.obj, keywords_, None)
		result = set(_process_words(result)) if result else None
		return list(result) if result else []

	def get_references(self):
		result = set()
		items = common.to_list(getattr(self.obj, references_, ()))
		for obj in items or ():
			adapted = search_interfaces.INTIIDResolver(obj, None)
			if adapted:
				ntiid = adapted.get_ntiid()
				if ntiid: result.add(unicode(ntiid))
		return list(result) if result else ()

	def get_inReplyTo(self):
		result = getattr(self.obj, inReplyTo_, None)
		return unicode(result) if result else None

@component.adapter(nti_interfaces.IHighlight)
@interface.implementer(search_interfaces.IHighlightContentResolver)
class _HighLightContentResolver(_ThreadableContentResolver):

	def get_content(self):
		result = self.obj.selectedText
		return result

@component.adapter(nti_interfaces.IRedaction)
@interface.implementer(search_interfaces.IRedactionContentResolver)
class _RedactionContentResolver(_HighLightContentResolver):

	def get_content(self):
		result = self.obj.selectedText
		return result

	def get_replacement_content(self):
		result = self.obj.replacementContent
		result = None if result and result.lower() == redaction_ else result
		return result

	def get_redaction_explanation(self):
		result = self.obj.redactionExplanation
		return result if result else None

class _PartsContentResolver(object):

	def _resolve(self, data):
		result = []
		items = common.to_list(data)
		for item in items or ():
			adapted = search_interfaces.IContentResolver(item, None)
			if adapted:
				result.append(adapted.get_content())
		result = u' '.join([x for x in result if x is not None])
		return result

@component.adapter(nti_interfaces.INote)
@interface.implementer(search_interfaces.INoteContentResolver)
class _NoteContentResolver(_ThreadableContentResolver, _PartsContentResolver):

	def get_title(self):
		return self.obj.title

	def get_content(self):
		return self._resolve(self.obj.body)

@component.adapter(chat_interfaces.IMessageInfo)
@interface.implementer(search_interfaces.IMessageInfoContentResolver)
class _MessageInfoContentResolver(_ThreadableContentResolver, _PartsContentResolver):

	def get_content(self):
		return self._resolve(self.obj.Body)

	def get_id(self):
		result = self.obj.ID
		return unicode(result) if result else None

	def get_channel(self):
		result = self.obj.channel
		return unicode(result) if result else None

	def get_recipients(self):
		data = getattr(self.obj, recipients_, None)
		return _process_words(data)

@component.adapter(Canvas)
class _CanvasShapeContentResolver(_BasicContentResolver, _PartsContentResolver):

	def get_content(self):
		return self._resolve(self.obj.shapeList)

@component.adapter(CanvasTextShape)
class _CanvasTextShapeContentResolver(_BasicContentResolver):

	def get_content(self):
		return self.obj.text

class _BlogContentResolverMixin(_AbstractIndexDataResolver, _PartsContentResolver):

	def get_title(self):
		return self.obj.title

	def get_content(self):
		result = self._resolve(self.obj.body)
		return result

	def get_tags(self):
		result = self.obj.tags
		result = _process_words(set(result)) if result else ()
		return result

	def get_id(self):
		result = None
		obj = self.obj
		if forum_interfaces.IHeadlinePost.providedBy(obj):
			obj = getattr(self.obj, '__parent__', None)
		if forum_interfaces.ITopic.providedBy(obj) or forum_interfaces.IPost.providedBy(obj):
			result = getattr(obj, 'id', None)
		return result or u''

@component.adapter(forum_interfaces.IPost)
@interface.implementer(search_interfaces.IPostContentResolver)
class _PostContentResolver(_BlogContentResolverMixin):
	pass

@component.adapter(forum_interfaces.IHeadlineTopic)
@interface.implementer(search_interfaces.IHeadlineTopicContentResolver)
class _HeadlineTopicContentResolver(_BlogContentResolverMixin):

	def __init__(self, obj):
		super(_HeadlineTopicContentResolver, self).__init__(obj.headline)
		self.topic = obj

@component.adapter(IDict)
@interface.implementer(search_interfaces.IHighlightContentResolver,
						search_interfaces.INoteContentResolver,
						search_interfaces.IRedactionContentResolver,
						search_interfaces.IMessageInfoContentResolver,
						search_interfaces.IPostContentResolver)
class _DictContentResolver(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = CaseInsensitiveDict(**obj)

	def _get_attr(self, names, default=None):
		for name in names:
			value = self.obj.get(name, None)
			if value is not None: return value
		return default

	# content resolver

	def get_content(self):
		return self.get_multipart_content(self.obj)

	def get_multipart_content(self, source):
		if isinstance(source, six.string_types):
			result = source
		elif isinstance(source, collections.Mapping):
			clazz = source.get(CLASS, u'').lower()
			if clazz == highlight_:
				result = source.get(selectedText_, u'')
			elif clazz == redaction_:
				result = source.get(selectedText_, u'')
			elif clazz == messageinfo_ or clazz == note_ or clazz == post_:
				result = []
				data = source.get(body_, source.get(BODY, u''))
				for item in common.to_list(data) or ():
					d = self.get_multipart_content(item)
					if d: result.append(d)
				result = ' '.join([x for x in result if x is not None])
			elif clazz == canvas_:
				result = []
				shapes = source.get('shapeList', ())
				for s in shapes or ():
					d = self.get_multipart_content(s)
					if d: result.append(d)
				result = ' '.join([x for x in result if x is not None])
			elif clazz == canvastextshape_:
				result = source.get(text_, u'')
			else:
				result = u''
		elif isinstance(source, collections.Iterable):
			items = []
			for item in source:
				items.append(self.get_multipart_content(item))
			result = ' '.join(items)
		else:
			result = u''

		result = unicode(result) if result else u''
		return result

	# user content resolver

	def get_title(self):
		result = self.obj.get(title_, ())
		return unicode(result) if result else None

	def get_ntiid(self):
		result = self.obj.get(NTIID)
		return unicode(result) if result else None

	def get_creator(self):
		result = self.obj.get(CREATOR)
		return unicode(result) if result else None

	def get_containerId(self):
		result = self.obj.get(CONTAINER_ID)
		return unicode(result) if result else None

	def get_keywords(self):
		result = self.obj.get(keywords_)
		result = set(_process_words(result)) if result else None
		return list(result) if result else []

	def get_tags(self):
		result = self.obj.get(tags_, self.obj.get(AUTO_TAGS, ()))
		return _process_words(result)

	def get_sharedWith(self):
		data = self.obj.get(sharedWith_, self.obj.get(flattenedSharingTargetNames_, ()))
		return _process_words(data)

	def get_last_modified(self):
		return self._get_attr(last_modified_fields)

	# treadable content resolver

	def get_references(self):
		result = set()
		data = self.obj.get(references_, u'')
		objects = data.split() if hasattr(data, 'split') else data
		for s in common.to_list(objects) or ():
			result.add(unicode(s))
		return list(result) if result else ()

	def get_inReplyTo(self):
		result = self.obj.get(inReplyTo_, u'')
		return result if result else None

	# redaction content resolver

	def get_replacement_content(self):
		result = self.obj.get(replacementContent_, None)
		return result if result else None

	def get_redaction_explanation(self):
		result = self.obj.get(redactionExplanation_, None)
		return result if result else None

	# messageinfo content resolver

	def get_id(self):
		result = self.obj.get(ID, None)
		return unicode(result) if result else None

	def get_channel(self):
		result = self.obj.get(channel_, None)
		return unicode(result) if result else None

	def get_recipients(self):
		data = self.obj.get(recipients_, ())
		return _process_words(data)

@component.adapter(search_interfaces.IBookContent)
@interface.implementer(search_interfaces.IBookContentResolver)
class _BookContentResolver(_BasicContentResolver):

	def get_content(self):
		return self.obj.content

	def get_ntiid(self):
		return self.obj.ntiid
	get_containerId = get_ntiid

	def get_last_modified(self):
		return self.obj.last_modified

@component.adapter(search_interfaces.IVideoTranscriptContent)
@interface.implementer(search_interfaces.IVideoTranscriptContentResolver)
class _VideoTranscriptContentResolver(_BasicContentResolver):

	def get_content(self):
		return self.obj.content

	def get_containerId(self):
		return self.obj.containerId

	def get_ntiid(self):
		return self.obj.videoId or self.get_containerId()

	def get_last_modified(self):
		return self.obj.last_modified

@component.adapter(search_interfaces.INTICardContent)
@interface.implementer(search_interfaces.INTICardContentResolver)
class _NTICardContentResolver(_BasicContentResolver):

	def get_content(self):
		return self.obj.content
	get_description = get_content

	def get_containerId(self):
		return self.obj.containerId

	def get_title(self):
		return self.obj.title

	def get_href(self):
		return self.obj.href

	def get_target_ntiid(self):
		return self.obj.target_ntiid

	def get_ntiid(self):
		return self.obj.ntiid

	def get_creator(self):
		return self.obj.creator

	def get_last_modified(self):
		return self.obj.last_modified

@interface.implementer(search_interfaces.IStopWords)
class _DefaultStopWords(object):

	def stopwords(self, language='en'):
		return ()

	def available_languages(self,):
		return ('en',)
