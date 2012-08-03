from __future__ import print_function, unicode_literals

import re
import six
import collections

from zope import component
from zope import interface
from persistent.interfaces import IPersistent

from dolmen.builtins import IDict

from nltk.tokenize import RegexpTokenizer

from nti.contentfragments import interfaces as frg_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import CanvasTextShape
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_ntiid_oid

from nti.contentsearch import to_list
from nti.contentsearch.interfaces import IContentResolver, IContentResolver2, IHighlightContentResolver, IRedactionContentResolver
from nti.contentsearch.interfaces import IContentTokenizer
from nti.contentsearch.common import (CLASS, BODY)
from nti.contentsearch.common import (text_, body_, selectedText_, replacementContent_, redactionExplanation_, 
									  creator_fields, keyword_fields, last_modified_fields, sharedWith_, 
									  container_id_fields, ntiid_fields, oid_fields, highlight_, note_,
									  messageinfo_, redaction_, canvas_, canvastextshape_, references_,
									  inReplyTo_, recipients_, channel_)


def get_content(text=None):
	result = component.getUtility(IContentTokenizer).tokenize(text) if text else u''
	return unicode(result)

@interface.implementer(IContentResolver2)
@component.adapter(basestring)
class _StringContentResolver(object):

	def __init__( self, content ):
		self.content = content

	def get_content(self):
		result = get_content(self.content) 
		return result if result else None
	
def _get_any_attr(obj, attrs):
	for a in attrs:
		try:
			value = getattr(obj, a, None)
		except:
			value = None
		if value is not None: return value
	return None

def _process_words(words):
	if words:
		if isinstance(words, six.string_types):
			words = [unicode(w.lower()) for w in words.split()]
		elif isinstance(words, collections.Iterable):
			words = [unicode(w.lower()) for w in words]
		else:
			words = []
	return words or []

@interface.implementer(IContentResolver2)
class _BasicContentaResolver(object):
	def __init__( self, obj ):
		self.obj = obj
		
class _AbstractIndexDataResolver(_BasicContentaResolver):
		
	def get_ntiid(self):
		return to_external_ntiid_oid( self.obj )
		
	def get_external_oid(self):
		return to_external_ntiid_oid( self.obj )
	get_oid = get_external_oid
	get_objectId = get_external_oid
	
	def get_creator(self):
		usr = _get_any_attr(self.obj, creator_fields)
		return usr.username if usr else None
	
	def get_containerId(self):
		result = _get_any_attr(self.obj, container_id_fields) 
		return unicode(result) if result else None

	def get_keywords(self):
		result = set()
		for name in keyword_fields:
			data = _get_any_attr(self.obj, [name])
			result.update(_process_words(data))
		return list(result) if result else []
	
	def get_sharedWith(self):
		data = _get_any_attr(self.obj, [sharedWith_])
		return _process_words(data)
	
	def get_last_modified(self):
		return _get_any_attr(self.obj, last_modified_fields)
	
class _ThreadableContentResolver(_AbstractIndexDataResolver):
	
	def get_references(self):
		items = to_list(_get_any_attr(self.obj, [references_]))
		result = set()
		for obj in items or ():
			adapted = component.queryAdapter(obj, IContentResolver2)
			ntiid = adapted.get_ntiid() if adapted else u''
			if ntiid: result.add(ntiid)
		return list(result) if result else []
	
	def get_inReplyTo(self):
		result = _get_any_attr(self.obj, [inReplyTo_]) 
		return unicode(result) if result else None
	
@component.adapter(nti_interfaces.IHighlight)
@interface.implementer(IHighlightContentResolver)
class _HighLightContentResolver2(_ThreadableContentResolver):

	def get_content(self):
		result = self.obj.selectedText
		return get_content(result)

@component.adapter(nti_interfaces.IRedaction)
@interface.implementer(IRedactionContentResolver)
class _RedactionContentResolver2(_HighLightContentResolver2):

	def get_content(self):
		result = [self.get_replacement_content(), self.get_redaction_explanation()]
		result.append(self.obj.selectedText)
		result = ' '.join([x for x in result if x is not None])
		return get_content(result)
	
	def get_replacement_content(self):
		result = self.obj.replacementContent
		result = get_content(result) if result else None
		if result and result.lower() == redaction_:
			result = None
		return result
		
	def get_redaction_explanation(self):
		result = self.obj.redactionExplanation
		return get_content(result) if result else None

class _PartsContentResolver(object):
	
	def _resolve(self, data):
		result = []
		items = to_list(data)
		for item in items or ():
			adapted = component.queryAdapter(item, IContentResolver2)
			result.append( adapted.get_content()  if adapted else u'')
		result = ' '.join([x for x in result if x is not None])
		return get_content(result)
	
@component.adapter(nti_interfaces.INote)
class _NoteContentResolver2(_ThreadableContentResolver, _PartsContentResolver):
	def get_content(self):
		return self._resolve(self.obj.body)
	
@component.adapter(chat_interfaces.IMessageInfo)
class _MessageInfoContentResolver2(_ThreadableContentResolver, _PartsContentResolver):
	def get_content(self):
		return self._resolve(self.obj.Body)
	
	def get_channel(self):
		result = self.obj.channel_
		return unicode(result) if result else None

	def get_recipients(self):
		data = _get_any_attr(self.obj, [recipients_])
		return _process_words(data)
	
@component.adapter(Canvas)
class _CanvasShapeContentResolver2(_BasicContentaResolver, _PartsContentResolver):
	def get_content(self):
		return self._resolve(self.obj.shapeList)

@component.adapter(CanvasTextShape)
class _CanvasTextShapeContentResolver2(_BasicContentaResolver):
	def get_content(self):
		return get_content(self.obj.text)
	
@interface.implementer(IContentResolver2)
@component.adapter(IDict)
class _DictContentResolver(object):
	
	def __init__( self, obj ):
		self.obj = obj
	
	def _get_attr(self, names, default=None):
		for name in names:
			value = self.obj.get(name, None)
			if value: return value
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
			elif clazz == messageinfo_ or clazz == note_:
				result = []
				data = source.get(body_, u'') if clazz == note_ else source.get(BODY, u'')
				for item in to_list(data) or ():
					d = self.get_multipart_content(item)
					if d: result.append(d)
				result = ' '.join([x for x in result if x is not None])
			elif clazz == canvas_:
				result = []
				shapes = source.get('shapeList', [])
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

		result = get_content(result) if result else u''
		return unicode(result)
	
	# user content resolver
	
	def get_ntiid(self):
		return self._get_attr(ntiid_fields)
		
	def get_external_oid(self):
		return self._get_attr(oid_fields)
	
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
		return list(result) if result else []
	
	def get_sharedWith(self):
		data = self._get_attr([sharedWith_])
		return _process_words(data)
	
	def get_last_modified(self):
		return self._get_attr(last_modified_fields)
		
	get_oid = get_external_oid
	get_objectId = get_external_oid
	
	# treadable content resolver 
	
	def get_references(self):
		data = self.obj.get(references_, u'')
		objects = data.split() if hasattr(data, 'split') else data
		result = set()
		for s in to_list(objects) or ():
			result.add(unicode(s))
		return list(result) if result else []
	
	def get_inReplyTo(self):
		return self._get_attr([inReplyTo_])
	
	# redaction content resolver
	
	def get_replacement_content(self):
		result = self.obj.get(replacementContent_, u'')
		return get_content(result) if result else None
		
	def get_redaction_explanation(self):
		result = self.obj.get(redactionExplanation_, u'')
		return get_content(result) if result else None
	
	# redaction content resolver
	
	def get_channel(self):
		result = self.obj.get(channel_, u'')
		return unicode(result) if result else None

	def get_recipients(self):
		data = self.obj.get(recipients_, None)
		return _process_words(data)
	
	
@interface.implementer( IContentTokenizer )
class _ContentTokenizer(object):
	tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*", flags = re.MULTILINE | re.DOTALL)

	def tokenize(self, text):
		if not text or not isinstance(text, six.string_types):
			return u''
		else:
			text = frg_interfaces.IUnicodeContentFragment(text)
			text = frg_interfaces.IPlainTextContentFragment(text)
			words = self.tokenizer.tokenize(text)
			text = ' '.join(words)
			return unicode(text)


# --------- 

@interface.implementer( IContentResolver )
class _HighLightContentResolver(object):
	def get_content(self, data):
		if nti_interfaces.IHighlight.providedBy(data):
			result = data.selectedText
		elif isinstance(data, collections.Mapping):
			result = data.get(selectedText_, u'')
		elif isinstance(data, six.string_types):
			result = unicode(data)
		else:
			result = u''
		return get_content(result)

@interface.implementer( IContentResolver )
class _RedactionContentResolver(object):
	def get_content(self, data):
		result = []
		if isinstance(data, six.string_types):
			result.append(unicode(data))
		else:
			for field in (replacementContent_, redactionExplanation_, selectedText_):
				if nti_interfaces.IRedaction.providedBy(data):
					d = getattr(data, field, u'')
					if d: result.append(d)
				elif isinstance(data, collections.Mapping):
					d = data.get(field, u'')
					if d: result.append(d)

		result = ' '.join([x for x in result if x is not None])
		return get_content(result)

@interface.implementer( IContentResolver )
class _NoteContentResolver(object):
	def get_content(self, data):
		body = ()
		result = []
		if nti_interfaces.INote.providedBy(data):
			body = to_list(data.body)
		elif isinstance(data, collections.Mapping):
			body = to_list(data.get(body_, u''))
		elif isinstance(data, six.string_types):
			body = [unicode(data)]

		for item in body:
			c = get_multipart_content(item)
			if c: result.append(c)
		return get_content(' '.join(result))


@interface.implementer( IContentResolver )
class _CanvasShapeContentResolver(object):
	def get_content(self, data):
		shapes = ()
		result = []
		if isinstance(data, Canvas):
			shapes = data.shapeList
		elif isinstance(data, collections.Mapping):
			shapes = data.get('shapeList', [])
		for s in shapes:
			c = get_multipart_content(s)
			if c: result.append(c)
		return get_content(' '.join(result))

@interface.implementer( IContentResolver )
class _CanvasTextShapeContentResolver(object):
	def get_content(self, data):
		if isinstance(data, CanvasTextShape):
			result = data.text
		elif isinstance(data, collections.Mapping):
			result = data.get(text_, u'')
		elif isinstance(data, six.string_types):
			result = data
		else:
			result = u''
		return unicode(result)

@interface.implementer( IContentResolver )
class _MessageInfoContentResolver(object):
	def get_content(self, data):
		body = ()
		result = []
		if chat_interfaces.IMessageInfo.providedBy(data):
			body = to_list(data.Body)
		elif isinstance(data, collections.Mapping):
			body = to_list(data.get(BODY, u''))
		elif isinstance(data, six.string_types):
			body = [data]

		for item in body:
			c = get_multipart_content(item)
			if c: result.append(c)
		return get_content(' '.join(result))

def get_multipart_content(source):
	if isinstance(source, six.string_types):
		result = source
	elif IPersistent.providedBy(source):
		name = source.__class__.__name__.lower()
		solver = component.queryUtility(IContentResolver, name=name)
		result = solver.get_content(source) if solver else u''
	elif isinstance(source, collections.Mapping):
		clazz = source.get(CLASS, u'')
		name = clazz.lower()
		solver = component.queryUtility(IContentResolver, name=name)
		result = solver.get_content(source) if solver else u''
	elif isinstance(source, collections.Iterable):
		items = []
		for item in source:
			if isinstance(item, six.string_types) and item:
				items.append(item)
			else:
				items.append(get_multipart_content(item))
		result = ' '.join(items)
	else:
		result = u''

	result = get_content(result) if result else u''
	return unicode(result)

def _process_text(text, lower=True):
	if text:
		return text.lower() if lower else text
	else:
		return None

def get_note_content(obj, lower=True, *args, **kwargs):
	solver = component.getUtility(IContentResolver, name="note")
	result = solver.get_content(obj)
	return _process_text(result, lower=lower)

def get_highlight_content(obj, lower=True, *args, **kwargs):
	solver = component.getUtility(IContentResolver, name="highlight")
	result = solver.get_content(obj)
	return _process_text(result, lower=lower)

def get_redaction_content(obj, lower=True, *args, **kwargs):
	solver = component.getUtility(IContentResolver, name="redaction")
	result = solver.get_content(obj)
	return _process_text(result, lower=lower)

def get_messageinfo_content(obj, lower=True, *args, **kwargs):
	solver = component.getUtility(IContentResolver, name="messageinfo")
	result = solver.get_content(obj)
	return _process_text(result, lower=lower)

def get_canvas_content(obj, lower=True, *args, **kwargs):
	solver = component.getUtility(IContentResolver, name="canvas")
	result = solver.get_content(obj)
	return _process_text(result, lower=lower)

def get_canvastextshape_content(obj, lower=True, *args, **kwargs):
	solver = component.getUtility(IContentResolver, name="canvastextshape")
	result = solver.get_content(obj)
	return _process_text(result, lower=lower)
