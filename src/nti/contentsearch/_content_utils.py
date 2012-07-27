from __future__ import print_function, unicode_literals

import re
import six
import collections

from zope import component
from zope import interface
from persistent.interfaces import IPersistent

from nltk.tokenize import RegexpTokenizer

from nti.contentfragments import interfaces as frg_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import CanvasTextShape
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import to_list
from nti.contentsearch.interfaces import IContentResolver
from nti.contentsearch.interfaces import IContentTokenizer
from nti.contentsearch.common import (CLASS, BODY)
from nti.contentsearch.common import (text_, body_, selectedText_, replacementContent_, redactionExplanation_)

def get_content(text=None):
	result = component.getUtility(IContentTokenizer).tokenize(text) if text else u''
	return unicode(result)

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
