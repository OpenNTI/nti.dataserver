from __future__ import print_function, unicode_literals

import sys
import time

from nti.contentsearch import zopyxtxng3corelogger
sys.modules["zopyx.txng3.core.logger"] = zopyxtxng3corelogger

from nti.contentsearch.common import to_list
from nti.contentsearch._search_query import QueryObject
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._ngrams_utils import (ngrams, ngram_tokens)
from nti.contentsearch._datastructures import LFUMap, CaseInsensitiveDict
from nti.contentsearch.common import (note_, highlight_, redaction_, messageinfo_)
from nti.contentsearch._search_highlights import (ngram_content_highlight, word_content_highlight)
from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT, WHOOSH_HIGHLIGHT)

import logging
logger = logging.getLogger( __name__ )

def get_indexable_types():
	return indexable_type_names

class SearchCallWrapper(object):
	def __init__(self, func):
		self.func = func

	def __call__(self, *args, **kargs):
		now = time.time()
		result =  self.func(*args, **kargs)
		elapsed = time.time() - now
		logger.debug('(%s,%r,%r) took %0.5fs' % (self.func.__name__, args, kargs, elapsed))
		return result
	
	def __get__(self, instance, owner):
		def wrapper(*args, **kargs):
			return self(instance, *args, **kargs)
		return wrapper
