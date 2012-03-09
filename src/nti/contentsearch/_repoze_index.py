import re
from time import mktime
from datetime import datetime
from collections import Iterable
from collections import OrderedDict

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from whoosh import analysis

from nltk import clean_html
from nltk.tokenize import RegexpTokenizer

from nti.dataserver.chat import MessageInfo
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import Highlight
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*", flags = re.MULTILINE | re.DOTALL)

# -----------------------------------

def to_list(data):
	if isinstance(data, basestring):
		data = [data]
	elif isinstance(data, list):
		pass
	elif isinstance(data, Iterable):
		data = list(data)
	elif data is not None:
		data = [data]
	return data

def epoch_time(dt):
	if dt:
		seconds = mktime(dt.timetuple())
		seconds += (dt.microsecond / 1000000.0)
		return seconds
	else:
		return 0

# -----------------------------------

def ngram_tokens(text, minsize=2, maxsize=10, at='start', unique=True):
	rext = analysis.RegexTokenizer()
	ngf = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	stream = rext(unicode(text))
	if not unique:
		result = [token.copy() for token in ngf(stream)]
	else:
		result = OrderedDict( {token.text:token.copy() for token in ngf(stream)}).values()
	return result
		
def ngrams(text):
	result = [token.text for token in ngram_tokens(text)]
	return ' '.join(sorted(result, cmp=lambda x,y: cmp(len(x),len(y))))

# -----------------------------------
	
def get_attr(obj, names, default=None):
	names = to_list(names)
	if isinstance(obj, dict):
		for name in names:
			value = obj.get(name,None)
			if value: return value
	else:
		for name in names:
			try:
				value = getattr(obj, name, None)
			except:
				value = None
			if value: return value
	return default

def _attrs(names):
	lexp = lambda x,y: get_attr(x, names,y)
	return lexp

# -----------------------------------

def _last_modified(obj, default):
	value  = get_attr(obj, ['lastModified', 'LastModified', 'last_modified', 'Last Modified'], default)
	if value:
		if isinstance(value, basestring):
			value = float(value)
		elif isinstance(value, datetime):
			value = epoch_time(value)
	else:
		value = 0
	return value

def _keywords(names,):
	def f(obj, default):
		words  = get_attr(obj, names, default)
		if words:
			if isinstance(words, basestring):
				words = words.split()
			elif isinstance(words, Iterable):
				words = [w for w in words]
			else:
				words = [words]
		return words
	return f
	
# -----------------------------------

def get_content(text, tokenizer=default_tokenizer):

	if not text or not isinstance(text, basestring):
		return u''

	text = clean_html(text)
	words = tokenizer.tokenize(text)
	text = ' '.join(words)
	return unicode(text)

def _content(names):
	def f(obj, default):
		value = get_attr(obj, names, default)
		value = get_content(value)
		return value
	return f

def get_multipart_content(source):
	
	gbls = globals()
			
	if isinstance(source, basestring):
		return get_content(source)
	elif isinstance(source, Iterable):
		
		def process_dict(d):
			clazz = item.get('Class', None)
			data = item.get('Items', None)
			if clazz and data:
				name = "get_%s_content" % clazz.lower()
				if name in gbls:
					return gbls[name](d)
			return u''
		
		items = []
		if isinstance(source, dict):
			items.append(process_dict(source))
		else:
			for item in source:
				if isinstance(item, basestring) and item:
					items.append(item)
					continue
				elif isinstance(item, dict):
					items.append(process_dict(item))
				else:
					items.add(get_multipart_content(item))
		return get_content(' '.join(items))
	elif not source:
		clazz = source.__class__.__name__
		name = "get_%s_content" % clazz.lower()
		if name in gbls:
			return gbls[name](source)
	return u''

def _multipart_content(names):
	def f(obj, default):
		source = get_attr(obj, names, default)
		result = get_multipart_content(source)
		return result
	return f

def _ngrams(names):
	def f(obj, default):
		source = get_attr(obj, names, default)
		result = ngrams(get_multipart_content(source))
		return result
	return f

# -----------------------------------

def get_highlight_content(data):
	if isinstance(data, dict):
		return data.get('startHighlightedFullText', u'')
	elif isinstance(data, Highlight):
		return getattr(data, 'startHighlightedFullText', u'')
	return u''

def get_canvas_content(data):
	result = []
	if isinstance(data, dict):
		shapes = data.get('shapeList', [])
	elif isinstance(data, Canvas):
		shapes = data.shapeList
		
	for s in shapes:
		c = get_multipart_content(s)
		if c: result.append(c)
	return ' '.join(result)

def get_note_content(data):
	result = []
	if isinstance(data, dict):
		body = to_list(data.get('body', u''))
	elif isinstance(data, Note):
		body = to_list(data.body)
		
	for item in body:
		c = get_multipart_content(item)
		if c: result.append(c)
	return ' '.join(result)

def get_messageinfo_content(data):
	result = []
	if isinstance(data, dict):
		body = to_list(data.get('body', u''))
	elif isinstance(data, MessageInfo):
		body = to_list(data.body)
	for item in body:
		c = get_multipart_content(item)
		if c: result.append(c)
	return ' '.join(result)

# -----------------------------------

def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog()
	catalog['last_modified'] = CatalogFieldIndex(_last_modified)
	catalog['oid'] = CatalogFieldIndex(_attrs(['OID','oid','id']))
	catalog['container'] = CatalogFieldIndex(_attrs(['ContainerId','containerId','container']))
	catalog['collectionId'] = CatalogFieldIndex(_attrs(['CollectionID','collectionId']))
	catalog['creator'] = CatalogFieldIndex(_attrs(['Creator','creator']))
	catalog['ntiid'] = CatalogFieldIndex(_attrs(['NTIID','ntiid']))
	catalog['keywords'] = CatalogKeywordIndex(_keywords(['keywords']))
	catalog['sharedWith'] = CatalogKeywordIndex(_keywords(['sharedWith']))
	return catalog

def create_notes_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog['ngrams'] = _create_text_index('ngrams', _ngrams(['body']))
	catalog['references'] = CatalogKeywordIndex(_keywords(['references']))
	catalog['content'] = _create_text_index('content', _multipart_content(['body']))
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog['color'] = CatalogFieldIndex(_attrs(['color']))
	catalog['ngrams'] = _create_text_index('ngrams', _ngrams(['startHighlightedFullText']))
	catalog['content'] = _create_text_index('content', _content(['startHighlightedFullText']))
	return catalog

def create_messageinfo_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog['id'] = CatalogFieldIndex(_attrs(['ID']))
	catalog['channel'] = CatalogFieldIndex(_attrs(['channel']))
	catalog['ngrams'] = _create_text_index('ngrams', _ngrams(['body']))
	catalog['content'] = _create_text_index('content', _multipart_content(['body']))
	catalog['references'] = CatalogKeywordIndex(_keywords(['references']))
	catalog['recipients'] = CatalogKeywordIndex(_keywords(['recipients']))
	return catalog

def create_catalog(type_name='Notes'):
	type_name = type_name[0:-1] if type_name.endswith('s') else type_name
	type_name = type_name.lower()
	if type_name == 'notes':
		return create_notes_catalog()
	elif type_name == 'highlight':
		return create_highlight_catalog()
	elif type_name =='messageinfo':
		return create_messageinfo_catalog()
	else:
		raise Exception("cannot create catalog for type '%s'" % type_name)
