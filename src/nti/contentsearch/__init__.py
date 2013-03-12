# -*- coding: utf-8 -*-
"""
Content search module.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys

# monkey patch

import BTrees

from zope.index.text.baseindex import BaseIndex

from repoze.catalog.query import BoolOp
from repoze.catalog.indexes.common import CatalogIndex

BoolOp.family = BTrees.family64
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

try:
	from . import zopyxtxng3_logger as ntizopy_logger
	sys.modules["zopyx.txng3.core.logger"] = ntizopy_logger

	from . import zopyxtxng3_storage as ntizopy_storage
	sys.modules["nti.contentsearch.zopyxtxng3corestorage"] = ntizopy_storage

	from . import zopyxtxng3_splitter as ntizopy_splitter
	sys.modules["nti.contentsearch.zopyxtxng3coresplitter"] = ntizopy_splitter


	from zopyx.txng3.core import index as zopyx_coreidx
	from zopyx.txng3.core import evaluator as zopyx_evaluator
	from zopyx.txng3.core import resultset as zopyx_resultset

	from . import zopyxtxng3_resultset as ntizopy_rs
	from . import zopyxtxng3_doclist as ntizopyx_doclist
	from . import zopyxtxng3_evaluator as ntizopyx_evaluator
	from . import zopyxtxng3_parsetree as ntizopyx_parsetree

	# change the evaluator to correct issue in getting the words
	# from the zopyx.txng3.core.parsetree nodes
	zopyx_coreidx.Evaluator = ntizopyx_evaluator.Evaluator

	# sometimes the nodes sent to the node splitter function are strings
	zopyx_coreidx.node_splitter = ntizopyx_parsetree.node_splitter

	for module in (zopyx_coreidx, zopyx_evaluator, zopyx_resultset, ntizopyx_evaluator):
		module.LOG = ntizopy_logger.LOG
		module.DocidList = ntizopyx_doclist.DocidList
		module.unionResultSets = ntizopy_rs.unionResultSets
		module.inverseResultSet = ntizopy_rs.inverseResultSet
		module.intersectionResultSets = ntizopy_rs.intersectionResultSets
except ImportError:
	pass

# legacy imports
from .common import indexable_type_names

def get_indexable_types():
	return indexable_type_names
