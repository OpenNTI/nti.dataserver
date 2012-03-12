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
	_library = component.queryUtility( ILibrary )
	if _library and containerId and is_valid_ntiid_string(containerId):
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

