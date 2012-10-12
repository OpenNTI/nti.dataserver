from __future__ import print_function, unicode_literals, absolute_import

import re
import six
import collections

from pkg_resources import resource_filename

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

from nti.contentsearch.common import to_list
from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch.common import (CLASS, BODY, ID)
from nti.contentsearch.common import (text_, body_, selectedText_, replacementContent_, redactionExplanation_,
									  creator_fields, keyword_fields, last_modified_fields, sharedWith_,
									  container_id_fields, ntiid_fields, oid_fields, highlight_, note_,
									  messageinfo_, redaction_, canvas_, canvastextshape_, references_,
									  inReplyTo_, recipients_, channel_, flattenedSharingTargetNames_)

import logging
logger = logging.getLogger( __name__ )

def get_punkt_translation_table(language='en'):
	table = component.queryUtility(search_interfaces.IPunktTranslationTable, name=language)
	return table or _default_punkt_translation_table()

def split_content(text, language='en'):
	tokenizer = component.getUtility(search_interfaces.IContentTokenizer, name=language)
	result = tokenizer.tokenize(unicode(text)) if text else []
	return result
	
def get_content(text=None, language='en'):
	result = ()
	text = unicode(text) if text else None
	if text:
		table = get_punkt_translation_table(language)
		result = split_content(text.translate(table))
	result = ' '.join(result)
	return unicode(result)

tokenize_content = get_content

@interface.implementer(search_interfaces.IContentResolver)
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

@interface.implementer(search_interfaces.IContentResolver)
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
		result = _get_any_attr(self.obj, creator_fields)
		if nti_interfaces.IEntity.providedBy(result):
			result = unicode(result.username)
		elif isinstance(result, six.string_types):
			result = unicode(result)
		else:
			result = None
		return result

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
		data = _get_any_attr(self.obj, [flattenedSharingTargetNames_, sharedWith_])
		return _process_words(data)

	def get_last_modified(self):
		result = _get_any_attr(self.obj, last_modified_fields)
		result = float(result) if result is not None else result
		return result

class _ThreadableContentResolver(_AbstractIndexDataResolver):

	def get_references(self):
		items = to_list(_get_any_attr(self.obj, [references_]))
		result = set()
		for obj in items or ():
			ntiid = None
			adapted = component.queryAdapter(obj, search_interfaces.IContentResolver)
			if adapted:
				if IPersistent.providedBy(obj):
					ntiid = adapted.get_ntiid()
				else:
					ntiid = adapted.get_content()
			if ntiid:
				result.add(unicode(ntiid))
		return list(result) if result else []

	def get_inReplyTo(self):
		result = _get_any_attr(self.obj, [inReplyTo_])
		return unicode(result) if result else None

@component.adapter(nti_interfaces.IHighlight)
@interface.implementer(search_interfaces.IHighlightContentResolver)
class _HighLightContentResolver(_ThreadableContentResolver):

	def get_content(self):
		result = self.obj.selectedText
		return get_content(result)

@component.adapter(nti_interfaces.IRedaction)
@interface.implementer(search_interfaces.IRedactionContentResolver)
class _RedactionContentResolver(_HighLightContentResolver):

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
			adapted = component.queryAdapter(item, search_interfaces.IContentResolver)
			result.append( adapted.get_content()  if adapted else u'')
		result = ' '.join([x for x in result if x is not None])
		return get_content(result)

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
		data = _get_any_attr(self.obj, [recipients_])
		return _process_words(data)

@component.adapter(Canvas)
class _CanvasShapeContentResolver(_BasicContentaResolver, _PartsContentResolver):
	def get_content(self):
		return self._resolve(self.obj.shapeList)

@component.adapter(CanvasTextShape)
class _CanvasTextShapeContentResolver(_BasicContentaResolver):
	def get_content(self):
		return get_content(self.obj.text)

@interface.implementer(search_interfaces.IContentResolver)
@component.adapter(IDict)
class _DictContentResolver(object):

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
		data = self.obj.get(sharedWith_, ()) or self.obj.get(flattenedSharingTargetNames_, ())
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
		result = self.obj.get(inReplyTo_, u'')
		return get_content(result) if result else None

	# redaction content resolver

	def get_replacement_content(self):
		result = self.obj.get(replacementContent_, u'')
		return get_content(result) if result else None

	def get_redaction_explanation(self):
		result = self.obj.get(redactionExplanation_, u'')
		return get_content(result) if result else None

	# redaction content resolver

	def get_id(self):
		result = self.obj.get(ID, None)
		return unicode(result) if result else None

	def get_channel(self):
		result = self.obj.get(channel_, None)
		return unicode(result) if result else None

	def get_recipients(self):
		data = self.obj.get(recipients_, ())
		return _process_words(data)

@interface.implementer( search_interfaces.IContentTokenizer )
class _ContentTokenizer(object):
	tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*",
								flags = re.MULTILINE | re.DOTALL | re.UNICODE)

	def tokenize(self, content):
		if not content or not isinstance(content, six.string_types):
			return ()
		
		plain_text = component.getAdapter( content, frg_interfaces.IPlainTextContentFragment, name='text' )
		words = self.tokenizer.tokenize(plain_text)
		return words
	
@interface.implementer( search_interfaces.IStopWords )
class _DefaultStopWords(object):
	
	def stopwords(self, language='en'):
		return ()

	def available_languages(self, ):
		return ('en',)
	

@interface.implementer( search_interfaces.IWordSimilarity )
class _DefaultWordSimilarity(object):
	
	def __init__(self):
		try:
			from zopyx.txng3.ext.levenshtein import ratio as zopyx_ratio
			self._ratio = zopyx_ratio
		except ImportError:
			self._ratio = lambda x,y: 1
			
	def compute(self, a, b):
		result = self._ratio(a,b)
		return result

	def rank(self, word, terms, reverse=True):
		result = sorted(terms, key=lambda w: self.compute(word, w), reverse=reverse)
		return result
	
def rank_words(word, terms, reverse=True):
	ws = component.getUtility(search_interfaces.IWordSimilarity)
	result = ws.rank(word, terms, reverse)
	return result

@interface.implementer( search_interfaces.IPunktTranslationTable )
def _default_punkt_translation_table():
	name = resource_filename(__name__, "punctuation-en.txt")
	with open(name, 'r') as src:
		lines = src.readlines()
	
	result = {}
	for line in lines:
		line = line.replace('\n', '')
		splits = line.split('\t')
		repl = splits[4] or None if len(splits) >= 5 else None
		result[int(splits[0])] = repl
	return result

