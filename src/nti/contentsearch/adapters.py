#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import collections

from zope import component
from zope import interface

from dolmen.builtins import IDict

from nti.chatserver.interfaces import IMessageInfo

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IRedaction
from nti.dataserver.interfaces import IReadableShared
from nti.dataserver.interfaces import IUseNTIIDAsExternalUsername

from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import CanvasTextShape
from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic

from nti.externalization.oids import to_external_ntiid_oid

from .common import to_list
from .common import get_type_name

from .content_utils import resolve_content_parts

from .interfaces import IACLResolver
from .interfaces import IBookContent
from .interfaces import ITypeResolver
from .interfaces import INTIIDResolver
from .interfaces import INTICardContent
from .interfaces import IContentResolver
from .interfaces import ICreatorResolver
from .interfaces import IBookContentResolver
from .interfaces import INoteContentResolver
from .interfaces import IPostContentResolver
from .interfaces import IForumContentResolver
from .interfaces import INTICardContentResolver
from .interfaces import IVideoTranscriptContent
from .interfaces import IHighlightContentResolver
from .interfaces import IRedactionContentResolver
from .interfaces import IShareableContentResolver
from .interfaces import IMessageInfoContentResolver
from .interfaces import IHeadlineTopicContentResolver
from .interfaces import IVideoTranscriptContentResolver

from .constants import content_, videotranscript_, nticard_, forum_
from .constants import inReplyTo_, recipients_, channel_, createdTime_
from .constants import redactionExplanation_, tag_fields, last_modified_fields
from .constants import sharedWith_, highlight_, note_, post_, tags_, messageinfo_ 
from .constants import redaction_, canvas_, canvastextshape_, references_, title_
from .constants import text_, body_, selectedText_, replacementContent_, keywords_
from .constants import flattenedSharingTargetNames_, lastModified_, created_time_fields

from .constants import CLASS, BODY, ID, NTIID, CREATOR, CONTAINER_ID, AUTO_TAGS

@interface.implementer(IContentResolver)
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

@interface.implementer(IContentResolver)
class _BasicContentResolver(object):

	def __init__(self, obj):
		self.obj = obj

@interface.implementer(ITypeResolver)
class _AbstractIndexDataResolver(_BasicContentResolver):

	@property
	def type(self):
		return get_type_name(self.obj)
	
	def get_ntiid(self):
		result = to_external_ntiid_oid(self.obj)
		return result
	ntiid = property(get_ntiid)

	def get_creator(self):
		result = self.obj.creator
		if IEntity.providedBy(result):
			if not IUseNTIIDAsExternalUsername.providedBy(result):
				result = unicode(result.username)
			else:
				result = result.NTIID
		result = unicode(result) if result else None
		return result
	creator = property(get_creator)

	def get_containerId(self):
		result = self.obj.containerId
		return unicode(result) if result else None
	containerId = property(get_containerId)

	def get_sharedWith(self):
		data = ()
		if IReadableShared.providedBy(self.obj):
			data = self.obj.flattenedSharingTargetNames
		result = _process_words(data)
		return result
	sharedWith = property(get_sharedWith)

	def get_flattenedSharingTargets(self):
		if IReadableShared.providedBy(self.obj):
			return self.obj.flattenedSharingTargets
		return ()
	flattenedSharingTargets = property(get_flattenedSharingTargets)

	def _get_date(self, name):
		result = getattr(self.obj, name, None)
		result = float(result) if result is not None else None
		return result

	def get_last_modified(self):
		return self._get_date(lastModified_)
	lastModified = property(get_last_modified)

	@property
	def createdTime(self):
		return self._get_date(createdTime_)

class _DefaultTagKeywordResolver(object):

	def __init__(self, obj):
		self.obj = obj

	def get_tags(self):
		result = set()
		for name in tag_fields:
			data = getattr(self.obj, name, ())
			result.update(_process_words(data))
		return list(result) if result else ()
	tags = property(get_tags)

	def get_keywords(self):
		result = getattr(self.obj, keywords_, None)
		result = set(_process_words(result)) if result else None
		return list(result) if result else ()
	keywords = property(get_keywords)

class _ThreadableContentResolver(_AbstractIndexDataResolver, _DefaultTagKeywordResolver):

	def get_references(self):
		result = set()
		items = to_list(getattr(self.obj, references_, ()))
		for obj in items or ():
			adapted = INTIIDResolver(obj, None)
			if adapted:
				ntiid = adapted.get_ntiid()
				if ntiid: result.add(unicode(ntiid))
		return list(result) if result else ()
	references = property(get_references)

	def get_inReplyTo(self):
		result = getattr(self.obj, inReplyTo_, None)
		return unicode(result) if result else None
	inReplyTo = property(get_inReplyTo)

@component.adapter(IHighlight)
@interface.implementer(IHighlightContentResolver)
class _HighLightContentResolver(_ThreadableContentResolver):

	def get_content(self):
		result = self.obj.selectedText
		return result
	content = property(get_content)

@component.adapter(IRedaction)
@interface.implementer(IRedactionContentResolver)
class _RedactionContentResolver(_HighLightContentResolver):

	def get_content(self):
		result = self.obj.selectedText
		return result
	content = property(get_content)

	def get_replacement_content(self):
		result = self.obj.replacementContent
		result = None if result and result.lower() == redaction_ else result
		return result
	replacementContent = property(get_replacement_content)

	def get_redaction_explanation(self):
		result = self.obj.redactionExplanation
		return result if result else None
	redactionExplanation = property(get_redaction_explanation)

class _PartsContentResolver(object):

	def _resolve(self, data):
		return resolve_content_parts(data)

@component.adapter(INote)
@interface.implementer(INoteContentResolver)
class _NoteContentResolver(_ThreadableContentResolver, _PartsContentResolver):

	def get_title(self):
		return self.obj.title
	title = property(get_title)

	def get_content(self):
		return self._resolve(self.obj.body)
	content = property(get_content)

@component.adapter(IMessageInfo)
@interface.implementer(IMessageInfoContentResolver)
class _MessageInfoContentResolver(_ThreadableContentResolver, _PartsContentResolver):

	def get_content(self):
		return self._resolve(self.obj.Body)
	content = property(get_content)

	def get_id(self):
		result = self.obj.ID
		return unicode(result) if result else None
	ID = id = property(get_id)

	def get_channel(self):
		result = self.obj.channel
		return unicode(result) if result else None
	channel = property(get_channel)

	def get_recipients(self):
		data = getattr(self.obj, recipients_, None)
		return _process_words(data)
	recipients = property(get_recipients)

@component.adapter(Canvas)
class _CanvasShapeContentResolver(_BasicContentResolver, _PartsContentResolver):

	def get_content(self):
		return self._resolve(self.obj.shapeList)
	content = property(get_content)

@component.adapter(CanvasTextShape)
class _CanvasTextShapeContentResolver(_BasicContentResolver):

	def get_content(self):
		return self.obj.text
	content = property(get_content)

class _BlogContentResolverMixin(_AbstractIndexDataResolver, _PartsContentResolver):

	def get_title(self):
		return self.obj.title
	title = property(get_title)

	def get_content(self):
		result = self._resolve(self.obj.body)
		return result
	content = property(get_content)

	def get_tags(self):
		result = self.obj.tags
		result = _process_words(set(result)) if result else ()
		return result
	tags = property(get_tags)

	def get_id(self):
		result = None
		obj = self.obj
		if IHeadlinePost.providedBy(obj):
			obj = getattr(self.obj, '__parent__', None)
		if 	ITopic.providedBy(obj) or IPost.providedBy(obj):
			result = getattr(obj, 'id', None)
		return result or u''
	ID = id = property(get_id)

@component.adapter(IPost)
@interface.implementer(IPostContentResolver)
class _PostContentResolver(_BlogContentResolverMixin):
	pass

@component.adapter(IHeadlineTopic)
@interface.implementer(IHeadlineTopicContentResolver)
class _HeadlineTopicContentResolver(_BlogContentResolverMixin):

	def __init__(self, obj):
		super(_HeadlineTopicContentResolver, self).__init__(obj.headline)
		self.topic = obj

@component.adapter(IGeneralForum)
@interface.implementer(IForumContentResolver)
class _ForumContentResolver(_AbstractIndexDataResolver):

	@property
	def type(self):
		return forum_

	def get_title(self):
		return self.obj.title
	title = property(get_title)

	def get_content(self):
		result = self.obj.description
		return result if result else None
	content = property(get_content)

@component.adapter(IDict)
@interface.implementer(IPostContentResolver,
					   INoteContentResolver,
					   IForumContentResolver,
					   IHighlightContentResolver,
					   IRedactionContentResolver,
					   IMessageInfoContentResolver)
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

	@property
	def type(self):
		return get_type_name(self.obj)

	def get_content(self):
		return self.get_multipart_content(self.obj)
	content = property(get_content)

	# user content resolver

	def get_title(self):
		result = self.obj.get(title_, ())
		return unicode(result) if result else None
	title = property(get_title)

	def get_ntiid(self):
		result = self.obj.get(NTIID)
		return unicode(result) if result else None
	ntiid = property(get_ntiid)

	def get_creator(self):
		result = self.obj.get(CREATOR)
		return unicode(result) if result else None
	creator = property(get_creator)

	def get_containerId(self):
		result = self.obj.get(CONTAINER_ID)
		return unicode(result) if result else None
	containerId = property(get_containerId)

	def get_keywords(self):
		result = self.obj.get(keywords_)
		result = set(_process_words(result)) if result else None
		return list(result) if result else ()
	keywords = property(get_keywords)

	def get_tags(self):
		result = self.obj.get(tags_, self.obj.get(AUTO_TAGS, ()))
		return _process_words(result)
	tags = property(get_tags)

	def get_sharedWith(self):
		data = self.obj.get(sharedWith_, self.obj.get(flattenedSharingTargetNames_, ()))
		return _process_words(data)
	sharedWith = property(get_sharedWith)

	def get_last_modified(self):
		return self._get_attr(last_modified_fields)
	lastModified = property(get_last_modified)

	def get_created_time(self):
		return self._get_attr(created_time_fields)
	createdTime = property(get_created_time)

	# treadable content resolver

	def get_references(self):
		result = set()
		data = self.obj.get(references_, u'')
		objects = data.split() if hasattr(data, 'split') else data
		for s in to_list(objects) or ():
			result.add(unicode(s))
		return list(result) if result else ()
	references = property(get_references)

	def get_inReplyTo(self):
		result = self.obj.get(inReplyTo_, u'')
		return result if result else None
	inReplyTo = property(get_inReplyTo)

	# redaction content resolver

	def get_replacement_content(self):
		result = self.obj.get(replacementContent_, None)
		return result if result else None
	replacementContent = property(get_replacement_content)

	def get_redaction_explanation(self):
		result = self.obj.get(redactionExplanation_, None)
		return result if result else None
	redactionExplanation = property(get_redaction_explanation)

	# messageinfo content resolver

	def get_id(self):
		result = self.obj.get(ID, None)
		return unicode(result) if result else None
	ID = id = property(get_id)

	def get_channel(self):
		result = self.obj.get(channel_, None)
		return unicode(result) if result else None
	channel = property(get_channel)

	def get_recipients(self):
		data = self.obj.get(recipients_, ())
		return _process_words(data)
	recipients = property(get_recipients)

@component.adapter(IBookContent)
@interface.implementer(IBookContentResolver)
class _BookContentResolver(_BasicContentResolver):

	@property
	def type(self):
		return content_

	def get_content(self):
		return self.obj.content
	content = property(get_content)

	def get_ntiid(self):
		return self.obj.ntiid
	get_containerId = get_ntiid
	ntiid = containerId = property(get_ntiid)

	def get_last_modified(self):
		return self.obj.last_modified
	createdTime = lastModified = property(get_last_modified)

@component.adapter(IVideoTranscriptContent)
@interface.implementer(IVideoTranscriptContentResolver)
class _VideoTranscriptContentResolver(_BasicContentResolver):

	@property
	def type(self):
		return videotranscript_

	def get_content(self):
		return self.obj.content
	content = property(get_content)

	def get_containerId(self):
		return self.obj.containerId
	containerId = property(get_containerId)

	def get_ntiid(self):
		return self.obj.videoId or self.get_containerId()
	videoId = ntiid = property(get_ntiid)

	def get_last_modified(self):
		return self.obj.last_modified
	createdTime = lastModified = property(get_last_modified)

@component.adapter(INTICardContent)
@interface.implementer(INTICardContentResolver)
class _NTICardContentResolver(_BasicContentResolver):

	@property
	def type(self):
		return nticard_

	def get_content(self):
		return self.obj.content
	get_description = get_content
	content = property(get_content)

	def get_containerId(self):
		return self.obj.containerId
	containerId = property(get_containerId)

	def get_title(self):
		return self.obj.title
	title = property(get_title)

	def get_href(self):
		return self.obj.href
	href = property(get_href)

	def get_target_ntiid(self):
		return self.obj.target_ntiid
	target_ntiid = property(get_target_ntiid)

	def get_ntiid(self):
		return self.obj.ntiid
	ntiid = property(get_ntiid)

	def get_creator(self):
		return self.obj.creator
	creator = property(get_creator)

	def get_last_modified(self):
		return self.obj.last_modified
	createdTime = lastModified = property(get_last_modified)

@interface.implementer(IACLResolver)
class _ACLResolver(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	@property
	def acl(self):
		obj = self.obj
		result = set()
		resolver = ICreatorResolver(obj, None)
		if resolver is not None:
			result.add(resolver.creator.lower())
		resolver = IShareableContentResolver(obj, None)
		if resolver is not None:
			result.update(x.lower() for x in resolver.sharedWith)
		return list(result) if result else None
