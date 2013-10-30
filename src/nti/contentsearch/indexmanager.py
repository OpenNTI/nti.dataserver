# -*- coding: utf-8 -*-
"""
Index manager creation methods.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import _indexmanager as search_manager
from . import interfaces  as search_interfaces
from . import _redis_indexmanager as redis_search_manager
from . import _whoosh_content_searcher as content_searcher

def create_index_manager_with_whoosh(indexdir=None,
									use_md5=True,
									max_users=100,
									parallel_search=True):
	content_idx_manager = content_searcher.wbm_factory()
	return search_manager.IndexManager(content_idx_manager,
								  	   search_interfaces.IWhooshEntityIndexManager,
								  	   parallel_search)

def create_index_manager_with_repoze(parallel_search=True):
	content_idx_manager = content_searcher.wbm_factory()
	return search_manager.IndexManager(content_idx_manager,
									   search_interfaces.IRepozeEntityIndexManager,
									   parallel_search)

def create_index_manager_with_repoze_redis(parallel_search=True):
	content_idx_manager = content_searcher.wbm_factory()
	return redis_search_manager._RedisIndexManager(
										content_idx_manager,
										search_interfaces.IRepozeEntityIndexManager,
										parallel_search)

create_index_manager = create_index_manager_with_repoze
