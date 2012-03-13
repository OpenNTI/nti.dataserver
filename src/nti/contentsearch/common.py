import re
from time import mktime
from collections import Iterable
from collections import OrderedDict

from zope import component

from whoosh import analysis
from whoosh import highlight

from nltk import clean_html
from nltk.tokenize import RegexpTokenizer

from nti.dataserver.interfaces import ILibrary
from nti.dataserver.ntiids import is_valid_ntiid_string

# -----------------------------------

default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*", flags = re.MULTILINE | re.DOTALL)

ID 				= 'ID'
HIT 			= 'Hit'
OID 			= 'OID'
TYPE 			= 'Type'
NTIID 			= 'NTIID'
CLASS 			= 'Class'
QUERY 			= 'Query'
ITEMS			= 'Items'
SNIPPET 		= 'Snippet'
CREATOR 		= 'Creator'
HIT_COUNT 		= 'Hit Count'
SUGGESTIONS		= 'Suggestions'
CONTAINER_ID	= 'ContainerID'
COLLECTION_ID	= 'CollectionID'
LAST_MODIFIED	= 'Last Modified'

id_				= 'id'
color_			= 'color'
ngrams_			= 'ngrams'
channel_		= 'channel'
content_		= 'content'
keywords_		= 'keywords'
references_		= 'references'
recipients_		= 'recipients'
sharedWith_		= 'sharedWith'

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

def get_collection(containerId, default='prealgebra'):
	result = default
	if containerId and is_valid_ntiid_string(containerId):
		_library = component.queryUtility( ILibrary )
		if _library:
			paths = _library.pathToNTIID(containerId)
			result = paths[0].label if paths else default
	return result.lower() if result else default

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
		
def highlight_content(query, text, maxchars=300, surround=50, order=highlight.FIRST, top=3, multiple_match=False):
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

# -----------------------------------

def get_content(text, tokenizer=default_tokenizer):
	"""
	return the text (words) to be indexed from the specified text

	the text is cleaned from any html tags then tokenized
	with the specified tokenizer.

	Based on nltk. Tokenizer should be domain specific
	"""
	
	if not text or not isinstance(text, basestring):
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
