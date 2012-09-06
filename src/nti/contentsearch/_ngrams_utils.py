from __future__ import print_function, unicode_literals

from collections import OrderedDict

from whoosh import analysis

import logging
logger = logging.getLogger( __name__ )

def ngram_tokens(text, minsize=3, maxsize=10, at='start', unique=True):
	tokenizer = analysis.RegexTokenizer()
	ng_filter = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	stream = tokenizer(unicode(text.lower()))
	if not unique:
		result = [token.copy() for token in ng_filter(stream)]
	else:
		result = OrderedDict( {token.text:token.copy() for token in ng_filter(stream)}).values()
	return result
		
def ngrams(text):
	if text:
		result = [token.text for token in ngram_tokens(text)]
		result = ' '.join(sorted(result, cmp=lambda x,y: cmp(x, y)))
	else:
		result = u''
	return unicode(result)
