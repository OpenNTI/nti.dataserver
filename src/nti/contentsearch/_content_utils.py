# -*- coding: utf-8 -*-
"""
Search content utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import collections

from zope import component
from zope import interface

from dolmen.builtins import IDict

from nti.contentprocessing import split_content
from nti.contentprocessing import get_content_translation_table

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import CanvasTextShape
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces

from nti.externalization.oids import to_external_ntiid_oid

from .common import to_list
from . import interfaces as search_interfaces

from .common import (CLASS, BODY, ID)
from .common import (text_, body_, selectedText_, replacementContent_, redactionExplanation_,
					 creator_fields, keyword_fields, last_modified_fields, sharedWith_,
					 container_id_fields, ntiid_fields,  highlight_, note_, post_, tags_,
					 messageinfo_, redaction_, canvas_, canvastextshape_, references_,
					 title_, inReplyTo_, recipients_, channel_, flattenedSharingTargetNames_)

def get_content(text=None, language='en'):
	result = ()
	text = unicode(text) if text else None
	if text:
		table = get_content_translation_table(language)
		result = split_content(text.translate(table))
	result = ' '.join(result)
	return unicode(result)

@interface.implementer(search_interfaces.IContentResolver)
@component.adapter(basestring)
class _StringContentResolver(object):

	__slots__ = ('content',)

	def __init__( self, content ):
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

	__slots__ = ('obj',)

	def __init__( self, obj ):
		self.obj = obj

class _AbstractIndexDataResolver(_BasicContentResolver):

	def get_ntiid(self):
		return to_external_ntiid_oid( self.obj )

	def get_creator(self):
		result = self.obj.creator
		if nti_interfaces.IEntity.providedBy(result):
			result = unicode(result.username)
		return unicode(result) if result else None

	def get_containerId(self):
		result = self.obj.containerId
		return unicode(result) if result else None

	def get_sharedWith(self):
		data = getattr(self.obj, flattenedSharingTargetNames_, ())
		return _process_words(data)

	def get_flattenedSharingTargets(self):
		if nti_interfaces.IReadableShared.providedBy( self.obj ):
			return self.obj.flattenedSharingTargets
		return ()

	def get_last_modified(self):
		result = self.obj.lastModified
		result = float(result) if result is not None else None
		return result

class _ThreadableContentResolver(_AbstractIndexDataResolver):

	def get_keywords(self):
		result = set()
		for name in keyword_fields:
			data = getattr(self.obj, name, None)
			result.update(_process_words(data))
		return list(result) if result else []

	def get_references(self):
		result = set()
		items = to_list(getattr(self.obj, references_, ()))
		for obj in items or ():
			adapted = component.queryAdapter(obj, search_interfaces.INTIIDResolver)
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
		result = [self.get_replacement_content(), self.get_redaction_explanation()]
		result.append(self.obj.selectedText)
		result = ' '.join([x for x in result if x is not None])
		return result

	def get_replacement_content(self):
		result = self.obj.replacementContent
		result = None if result and result.lower() == redaction_ else result
		return result

	def get_redaction_explanation(self):
		result = self.obj.redactionExplanation
		return result

class _PartsContentResolver(object):

	def _resolve(self, data):
		result = []
		items = to_list(data)
		for item in items or ():
			adapted = component.queryAdapter(item, search_interfaces.IContentResolver)
			result.append( adapted.get_content()  if adapted else u'')
		result = ' '.join([x for x in result if x is not None])
		return result

@component.adapter(nti_interfaces.INote)
@interface.implementer(search_interfaces.INoteContentResolver)
class _NoteContentResolver(_ThreadableContentResolver, _PartsContentResolver):
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

@component.adapter(for_interfaces.IPost)
@interface.implementer(search_interfaces.IPostContentResolver)
class _PostContentResolver(_AbstractIndexDataResolver, _PartsContentResolver):

	def get_title(self):
		return self.obj.title

	def get_content(self):
		return self._resolve(self.obj.body)

	def get_tags(self):
		result = self.obj.tags
		result = _process_words(set(result)) if result else ()
		return result

	def get_id(self):
		result = None
		obj = self.obj
		if for_interfaces.IHeadlinePost.providedBy(obj):
			obj = getattr(self.obj, '__parent__', None)
		if 	for_interfaces.IHeadlineTopic.providedBy(obj) or \
			for_interfaces.IPersonalBlogComment.providedBy(obj):
			result = getattr(obj,'id', None)
		return result or u''

@component.adapter(IDict)
@interface.implementer(	search_interfaces.IHighlightContentResolver,
						search_interfaces.INoteContentResolver,
						search_interfaces.IRedactionContentResolver,
						search_interfaces.IMessageInfoContentResolver,
						search_interfaces.IPostContentResolver,)
class _DictContentResolver(object):

	__slots__ = ('obj',)

	def __init__( self, obj ):
		self.obj = obj

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
				result = []
				for field in (replacementContent_, redactionExplanation_, selectedText_):
					d = source.get(field, u'')
					if d: result.append(d)
				result = ' '.join([x for x in result if x is not None])
			elif clazz == messageinfo_ or clazz == note_ or clazz == post_:
				result = []
				data = source.get(body_, source.get(BODY, u''))
				for item in to_list(data) or ():
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

	def get_ntiid(self):
		return self._get_attr(ntiid_fields)

	def get_creator(self):
		result = self._get_attr(creator_fields)
		return unicode(result) if result else None

	def get_containerId(self):
		result =  self._get_attr(container_id_fields)
		return unicode(result) if result else None

	def get_keywords(self):
		result = set()
		for name in keyword_fields:
			data = self._get_attr([name])
			result.update(_process_words(data))
		return list(result) if result else ()

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
		for s in to_list(objects) or ():
			result.add(unicode(s))
		return list(result) if result else ()

	def get_inReplyTo(self):
		result = self.obj.get(inReplyTo_, u'')
		return result if result else None

	# redaction content resolver

	def get_replacement_content(self):
		result = self.obj.get(replacementContent_, u'')
		return result if result else None

	def get_redaction_explanation(self):
		result = self.obj.get(redactionExplanation_, u'')
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

	# post content resolver

	def get_title(self):
		result = self.obj.get(title_, ())
		return unicode(result) if result else None

	def get_tags(self):
		result = self.obj.get(tags_, ())
		return _process_words(result)

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

@interface.implementer( search_interfaces.IStopWords )
class _DefaultStopWords(object):

	def stopwords(self, language='en'):
		return ()

	def available_languages(self, ):
		return ('en',)
