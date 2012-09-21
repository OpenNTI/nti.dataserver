from __future__ import print_function, unicode_literals

import sys
import time

# monkey patch

from nti.contentsearch import zopyxtxng3corelogger
sys.modules["zopyx.txng3.core.logger"] = zopyxtxng3corelogger

from zopyx.txng3.core import index as zopycoreidx
from zopyx.txng3.core import evaluator as zopyevaluator

from nti.contentsearch import zopyxtxng3coreresultset as ntizopy_rs
from nti.contentsearch import zopyxtxng3coredoclist as ntizopyx_doclist

for module in (zopycoreidx, zopyevaluator):
	module.LOG = zopyxtxng3corelogger.LOG
	module.DocidList = ntizopyx_doclist.DocidList
	module.unionResultSets = ntizopy_rs.unionResultSets
	module.inverseResultSet = ntizopy_rs.inverseResultSet
	module.intersectionResultSets = ntizopy_rs.intersectionResultSets
	
# legacy imports

from nti.contentsearch.common import indexable_type_names

def get_indexable_types():
	return indexable_type_names

import logging
logger = logging.getLogger( __name__ )

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
