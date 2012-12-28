from __future__ import print_function, unicode_literals

import sys
import time

# monkey patch

import BTrees

from zope.index.text.baseindex import BaseIndex

from repoze.catalog.query import BoolOp
from repoze.catalog.indexes.common import CatalogIndex

BoolOp.family = BTrees.family64
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

from nti.contentsearch import zopyxtxng3corelogger
sys.modules["zopyx.txng3.core.logger"] = zopyxtxng3corelogger

from zopyx.txng3.core import index as zopyx_coreidx
from zopyx.txng3.core import evaluator as zopyx_evaluator
from zopyx.txng3.core import resultset as zopyx_resultset

from nti.contentsearch import zopyxtxng3coreresultset as ntizopy_rs
from nti.contentsearch import zopyxtxng3coredoclist as ntizopyx_doclist
from nti.contentsearch import zopyxtxng3coreevaluator as ntizopyx_evaluator
from nti.contentsearch import zopyxtxng3coreparsetree as ntizopyx_parsetree

# change the evaluator to correct issue in getting the words 
# from the zopyx.txng3.core.parsetree nodes
zopyx_coreidx.Evaluator = ntizopyx_evaluator.Evaluator

# sometimes the nodes sent to the node splitter function are strings
zopyx_coreidx.node_splitter = ntizopyx_parsetree.node_splitter

for module in (zopyx_coreidx, zopyx_evaluator, zopyx_resultset, ntizopyx_evaluator):
	module.LOG = zopyxtxng3corelogger.LOG
	module.DocidList = ntizopyx_doclist.DocidList
	module.unionResultSets = ntizopy_rs.unionResultSets
	module.inverseResultSet = ntizopy_rs.inverseResultSet
	module.intersectionResultSets = ntizopy_rs.intersectionResultSets
	
# legacy imports
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._whoosh_index import create_book_schema

def get_indexable_types():
	return indexable_type_names
