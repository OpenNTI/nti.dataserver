from __future__ import print_function, unicode_literals

from collections import OrderedDict

from whoosh import analysis

import logging
logger = logging.getLogger( __name__ )

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
	if text:
		result = [token.text for token in ngram_tokens(text)]
		result = ' '.join(sorted(result, cmp=lambda x,y: cmp(x, y)))
	else:
		result = u''
	return unicode(result)
