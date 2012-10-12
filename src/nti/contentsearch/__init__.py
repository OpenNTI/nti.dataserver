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

import logging
logger = logging.getLogger( __name__ )

from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._content_utils import get_punkt_translation_table as get_punctuation_translation_table

def get_indexable_types():
	return indexable_type_names
