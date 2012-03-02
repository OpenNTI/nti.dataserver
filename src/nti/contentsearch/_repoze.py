import re
import collections
from time import mktime
from datetime import datetime

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nltk import clean_html
from nltk.tokenize import RegexpTokenizer

from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import Highlight

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
	elif isinstance(data, collections.Iterable):
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

def _last_modified(obj, default=0):
	value  = get_attr(obj, ['lastModified', 'Last Modified'], default)
	if value:
		if isinstance(value, basestring):
			value = float(value)
		elif isinstance(value, datetime):
			value = epoch_time(value)
	else:
		value = 0
	return value

def _keywords(names, _default=[]):
	
	def f(obj, default=_default):
		words  = get_attr(obj, names, default)
		if words:
			if isinstance(words, basestring):
				words = words.split()
			elif isinstance(words, collections.Iterable):
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

def _content(names, _default=None):
	def f(obj, default=_default):
		value = get_attr(obj, names, default)
		return get_content(value)
	return f

def get_multipart_content(source):
	
	gbls = globals()
			
	if isinstance(source, basestring):
		return get_content(source)
	elif isinstance(source, collections.Iterable):
		
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

def _multipart_content(names, _default=None):
	def f(obj, default=_default):
		source = get_attr(obj, names, default)
		return get_multipart_content(source) if source else default
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

# -----------------------------------

def _create_treadable_mixin_catalog():
	catalog = Catalog()
	catalog['lastModified'] = CatalogFieldIndex(_last_modified)
	catalog['id'] = CatalogFieldIndex(_attrs(['OID','oid','id']))
	catalog['container'] = CatalogFieldIndex(_attrs(['ContainerId','containerId','container']))
	catalog['collectionId'] = CatalogFieldIndex(_attrs(['CollectionID','collectionId']))
	catalog['creator'] = CatalogFieldIndex(_attrs(['Creator','creator']))
	catalog['ntiid'] = CatalogFieldIndex(_attrs(['NTIID','ntiid']))
	catalog['keywords'] = CatalogKeywordIndex(_keywords(['keywords']))
	catalog['sharedWith'] = CatalogKeywordIndex(_keywords(['sharedWith']))
	return catalog

def create_notes_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog['references'] = CatalogKeywordIndex(_keywords(['references']))
	catalog['body'] = CatalogTextIndex(_multipart_content(['body']))
	#catalog['quick'] = CatalogTextIndex('quick')
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog['color'] = CatalogFieldIndex(_attrs(['color']))
	catalog['startHighlightedFullText'] = CatalogTextIndex(_content(['startHighlightedFullText']))
	return catalog

