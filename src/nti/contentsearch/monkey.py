# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import BTrees

def patch_zope_index():
	from zope.index.text.baseindex import BaseIndex
	BaseIndex.family = BTrees.family64

def patch_repoze():
	from repoze.catalog.query import BoolOp
	from repoze.catalog.indexes.common import CatalogIndex

	BoolOp.family = BTrees.family64
	CatalogIndex.family = BTrees.family64

def patch_zopyx():
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
	except ImportError, e:
		logger.exeption("Error patching zopyx", e)
		raise

def patch_imports():
	# TODO: can we use zope.deferedimport
	from . import content_utils
	sys.modules["nti.contentsearch._content_utils"] = content_utils

	from . import discriminators
	sys.modules["nti.contentsearch._discriminators"] = discriminators

def patch():
	patch_zopyx()
	patch_repoze()
	patch_imports()
	patch_zope_index()
