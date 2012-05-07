import re
import six
import time
from time import mktime
from datetime import datetime
from collections import Iterable
from collections import OrderedDict

from zope import component
from persistent.interfaces import IPersistent

from whoosh import analysis
from whoosh import highlight

from nltk import clean_html
from nltk.tokenize import RegexpTokenizer

from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.externalization import interfaces as ext_interfaces

from nti.chatserver.messageinfo import MessageInfo

from nti.dataserver.users import Entity
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import Highlight
from nti.dataserver.contenttypes import CanvasTextShape
from nti.externalization.oids import to_external_ntiid_oid
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentsearch import to_list

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*", flags = re.MULTILINE | re.DOTALL)
	
ID 				= unicode(ext_interfaces.StandardExternalFields.ID)
HIT 			= u'Hit'
OID 			= unicode(ext_interfaces.StandardExternalFields.OID)
TYPE 			= u'Type'
BODY			= u'Body'
NTIID 			= unicode(ext_interfaces.StandardExternalFields.NTIID)
CLASS 			= u'Class'
QUERY 			= u'Query'
ITEMS			= u'Items'
CONTENT			= u'Content'
SNIPPET 		= u'Snippet'
CREATOR 		= unicode(ext_interfaces.StandardExternalFields.CREATOR)
AUTO_TAGS		= u'AutoTags'
MIME_TYPE		= unicode(ext_interfaces.StandardExternalFields.MIMETYPE)
HIT_COUNT 		= u'Hit Count'
TARGET_OID		= u'TargetOID'
MESSAGE_INFO	= u'MessageInfo'
SUGGESTIONS		= u'Suggestions' 
CONTAINER_ID	= unicode(ext_interfaces.StandardExternalFields.CONTAINER_ID)
COLLECTION_ID	= u'CollectionId'
LAST_MODIFIED	= unicode(ext_interfaces.StandardExternalFields.LAST_MODIFIED)

	
id_				= unicode(ext_interfaces.StandardInternalFields.ID)
oid_			= u'oid'
body_ 			= u'body'
text_			= u'text'
type_			= u'type'
tags_			= u'tags'
quick_			= u'quick'
title_			= u'title'
ntiid_			= unicode(ext_interfaces.StandardInternalFields.NTIID)
color_			= u'color'
p_oid_			= u'_p_oid'
title_			= u'title'
ngrams_			= u'ngrams'
channel_		= u'channel'
section_		= u'section'
username_		= u'username'
creator_		= unicode(ext_interfaces.StandardInternalFields.CREATOR)
related_		= u'related'
content_		= u'content'
keywords_		= u'keywords'
references_		= u'references'
recipients_		= u'recipients'
sharedWith_		= u'sharedWith'
containerId_	= unicode(ext_interfaces.StandardInternalFields.CONTAINER_ID)
collectionId_	= u'collectionId'
last_modified_	= u'last_modified'
startHighlightedFullText_ = 'startHighlightedFullText'

ntiid_fields = [NTIID, ntiid_]
creator_fields = [CREATOR, creator_]
oid_fields = [OID, p_oid_, oid_, id_]
keyword_fields = [keywords_, tags_, AUTO_TAGS]
container_id_fields = [CONTAINER_ID, 'ContainerID', containerId_, 'container']
last_modified_fields =  [LAST_MODIFIED, ext_interfaces.StandardInternalFields.LAST_MODIFIED,
						 ext_interfaces.StandardInternalFields.LAST_MODIFIEDU, '_lastModified', last_modified_]

nti_mimetype_prefix = 'application/vnd.nextthought.'

note_ = u'note'
highlight_ = u'highlight'
messageinfo = u'messageinfo'
indexable_type_names = (note_, highlight_, messageinfo)

WORD_HIGHLIGHT  = "WordHighlight"
NGRAM_HIGHLIGHT = "NGRAMHighlight"

# -----------------------------------

def get_attr(obj, names, default=None):
	if not obj: return default
	
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

def epoch_time(dt):
	if dt:
		seconds = mktime(dt.timetuple())
		seconds += (dt.microsecond / 1000000.0)
		return seconds
	else:
		return 0
	
def echo(x):
	return unicode(x) if x else u''

def get_datetime(x=None):
	f = time.time()
	if x:
		f = float(x) if isinstance(x, six.string_types) else x
	return datetime.fromtimestamp(f)

def get_keywords(records):
	result = ''
	if records:
		result = ','.join(records)
	return unicode(result)

# -----------------------------------

def normalize_type_name(x, encode=True):
	result = ''
	if x:
		result =x[0:-1].lower() if x.endswith('s') else x.lower()
	return unicode(result) if encode else result
	
def get_type_name(obj):
	if not isinstance(obj, dict):
		result = obj.__class__.__name__
	elif CLASS in obj:
		result = obj[CLASS]
	elif MIME_TYPE in obj:
		result = obj[MIME_TYPE]
		if result and result.startswith(nti_mimetype_prefix):
			result = result[len(nti_mimetype_prefix):]
	else:
		result = None
	return normalize_type_name(result) if result else u''

def get_collection(ntiid, default=None, registry=component):
	result = default
	if ntiid and is_valid_ntiid_string(ntiid):
		_library = registry.queryUtility( IContentPackageLibrary )
		if _library:
			paths = _library.pathToNTIID(ntiid)
			result = paths[0].label if paths else default
	return unicode(result.lower()) if result else default

# -----------------------------------

def get_external_oid(obj, default=None):
	if IPersistent.providedBy(obj):
		result = to_external_ntiid_oid( obj )
	else:
		result = obj if isinstance(obj, six.string_types) else get_attr(obj, oid_fields)
	return unicode(result) if result else None
		
def get_ntiid(obj, default=None):
	if IPersistent.providedBy(obj):
		result = to_external_ntiid_oid( obj )
	else:
		result = obj if isinstance(obj, six.string_types) else get_attr(obj, ntiid_fields)
	return unicode(result) if result else None

def get_creator(obj, default=None):
	result = obj if isinstance(obj, six.string_types) else get_attr(obj, creator_fields)
	if isinstance(result, Entity):
		result = result.username
	return unicode(result) if result else None

def get_references(obj, default=None):
	objects = obj.split() if hasattr(obj, 'split') else get_attr(obj, [references_], default)
	try:
		iterable = iter(objects)
	except TypeError:
		iterable = (objects,)

	result = set()
	for obj in iterable:
		if isinstance(obj, six.string_types):
			for s in obj.split():
				result.add(unicode(s))
		else:
			ntiid = get_ntiid(obj)
			if ntiid: result.add(ntiid)
	return list(result) if result else []

def get_last_modified(obj, default=None):
	value = get_attr(obj, last_modified_fields, default)
	if value:
		if isinstance(value, six.string_types):
			value = float(value)
		elif isinstance(value, datetime):
			value = epoch_time(value)
	else:
		value = 0
	return value

# -----------------------------------

def get_multipart_content(source):
	
	gbls = globals()
			
	if isinstance(source, six.string_types):
		return get_content(source)
	elif IPersistent.providedBy(source):
		clazz = source.__class__.__name__
		name = "get_%s_content" % clazz.lower()
		if name in gbls:
			return gbls[name](source)
	elif isinstance(source, Iterable):
		
		def process_dict(d):
			clazz = d.get(CLASS, None)
			if clazz:
				name = "get_%s_content" % clazz.lower()
				if name in gbls:
					return gbls[name](d)
			return u''
		
		items = []
		if isinstance(source, dict):
			items.append(process_dict(source))
		else:
			for item in source:
				if isinstance(item, six.string_types) and item:
					items.append(item)
					continue
				elif isinstance(item, dict):
					items.append(process_dict(item))
				else:
					items.append(get_multipart_content(item))
		return get_content(' '.join(items))
	return u''

def get_highlight_content(data):
	if isinstance(data, dict):
		result = data.get(startHighlightedFullText_, u'')
	elif isinstance(data, Highlight):
		result = getattr(data, startHighlightedFullText_, u'')
	else:
		result = u''
	return unicode(result)

def get_canvas_content(data):
	result = []
	if isinstance(data, dict):
		shapes = data.get('shapeList', [])
	elif isinstance(data, Canvas):
		shapes = data.shapeList
		
	for s in shapes:
		c = get_multipart_content(s)
		if c: result.append(c)
	return unicode(' '.join(result))

def get_note_content(data):
	result = []
	if isinstance(data, dict):
		body = to_list(data.get(body_, u''))
	elif isinstance(data, Note):
		body = to_list(data.body)
	else:
		body =  ()
		
	for item in body:
		c = get_multipart_content(item)
		if c: result.append(c)
	return unicode(' '.join(result))

def get_messageinfo_content(data):
	result = []
	if isinstance(data, dict):
		body = to_list(data.get(body_, u''))
	elif isinstance(data, MessageInfo):
		body = to_list(data.body)
	else:
		body =  ()
	for item in body:
		c = get_multipart_content(item)
		if c: result.append(c)
	return unicode(' '.join(result))

def get_canvastextshape_content(data):
	if isinstance(data, dict):
		result = data.get(text_, u'')
	elif isinstance(data, CanvasTextShape):
		result = data.text
	else:
		result = u''
	return unicode(result)

# -----------------------------------

def ngram_tokens(text, minsize=3, maxsize=10, at='start', unique=True):
	rext = analysis.RegexTokenizer()
	ngf = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	stream = rext(unicode(text.lower()))
	if not unique:
		result = [token.copy() for token in ngf(stream)]
	else:
		result = OrderedDict( {token.text:token.copy() for token in ngf(stream)}).values()
	return result
		
def ngrams(text):
	result = [token.text for token in ngram_tokens(text)]
	result = ' '.join(sorted(result, cmp=lambda x,y: cmp(x, y)))
	return unicode(result)

# -----------------------------------

def set_matched_filter(tokens, termset, text, multiple_match=True):
	index = {} if multiple_match else None
	for t in tokens:
		t.matched = t.text in termset
		if t.matched:
			
			idx = 0
			if multiple_match:
				a = index.get(t.text, None)
				if not a:
					a = [0]
					index[t.text] = a
				idx = a[-1]
				
			t.startchar = text.find(t.text, idx)
			t.endchar = t.startchar + len(t.text)
			
			if multiple_match:
				a.append(t.startchar+1)
		else:
			t.startchar = 0
			t.endchar = len(text)
		yield t
		
def ngram_content_highlight(query, text, maxchars=300, surround=50, order=highlight.FIRST, top=3, 
							multiple_match=False, *args, **kwargs):
	"""
	highlight based on ngrams
	"""
	text = unicode(text)
	text_lower = unicode(text.lower())
	
	query = unicode(query.lower())
	termset = frozenset([query])
		
	scorer = highlight.BasicFragmentScorer()
	tokens = ngram_tokens(text_lower, unique=not multiple_match)
	tokens = set_matched_filter(tokens, termset, text_lower, multiple_match)
	
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	fragments = fragmenter.fragment_tokens(text, tokens)
	fragments = highlight.top_fragments(fragments, top, scorer, order)
	
	formatter = highlight.UppercaseFormatter()
	return formatter(text, fragments)

def word_content_highlight(query, text, analyzer=None, maxchars=300, surround=50, *args, **kwargs):
	"""
	whoosh highlight based on words
	"""
	terms = frozenset([query])
	analyzer = analyzer or analysis.SimpleAnalyzer()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	formatter = highlight.UppercaseFormatter()
	return highlight.highlight(text, terms, analyzer, fragmenter, formatter)

# -----------------------------------

def get_content(text, tokenizer=default_tokenizer):
	"""
	return the text (words) to be indexed from the specified text

	the text is cleaned from any html tags then tokenized
	with the specified tokenizer.

	Based on nltk. Tokenizer should be domain specific
	"""
	
	if not text or not isinstance(text, six.string_types):
		return u''

	text = clean_html(text)
	words = tokenizer.tokenize(text)
	text = ' '.join(words)
	return unicode(text)

# -----------------------------------

def _empty_result(query, is_suggest=False):
	result = {}
	result[QUERY] = query
	result[HIT_COUNT] = 0
	result[ITEMS] = [] if is_suggest else {}
	result[LAST_MODIFIED] = 0
	return result

def empty_search_result(query):
	return _empty_result(query)

def empty_suggest_and_search_result(query):
	result = _empty_result(query)
	result[SUGGESTIONS] = []
	return result

def empty_suggest_result(word):
	return _empty_result(word, True)

def merge_search_results(a, b):

	if not a and not b:
		return None
	elif not a and b:
		return b
	elif a and not b:
		return a

	alm = a.get(LAST_MODIFIED, 0)
	blm = b.get(LAST_MODIFIED, 0)
	a[LAST_MODIFIED] = max(alm, blm)

	if not a.has_key(ITEMS):
		a[ITEMS] = {}
	
	a[ITEMS].update(b.get(ITEMS, {}))
	a[HIT_COUNT] = len(a[ITEMS])
	return a

def merge_suggest_and_search_results(a, b):
	result = merge_search_results(a, b)
	s_a = set(a.get(SUGGESTIONS, [])) if a else set([])
	s_b = set(b.get(SUGGESTIONS, [])) if b else set([])
	s_a.update(s_b)
	result[SUGGESTIONS] = list(s_a)
	return result

def merge_suggest_results(a, b):

	if not a and not b:
		return None
	elif not a and b:
		return b
	elif a and not b:
		return a

	alm = a.get(LAST_MODIFIED, 0)
	blm = b.get(LAST_MODIFIED, 0)
	a[LAST_MODIFIED] = max(alm, blm)

	if not a.has_key(ITEMS):
		a[ITEMS] = []
	
	a_set = set(a.get(ITEMS,[]))
	a_set.update(b.get(ITEMS,[]))
	a[ITEMS] = list(a_set)
	a[HIT_COUNT] = len(a[ITEMS])
	return a

# -----------------------------------

class QueryExpr(object):
	def __init__(self, expr):
		assert expr is not None, 'must specify a query expression'
		self.expr = unicode(expr)
	
	def __str__( self ):
		return self.expr

	def __repr__( self ):
		return 'QueryExpr(%s)' % self.expr

_all_re = re.compile('([\?\*])')
def is_all_query(query):
	mo = _all_re.search(query)
	return mo and mo.start(1) == 0
