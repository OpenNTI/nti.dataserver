# -*- coding: utf-8 -*-
"""
Index manager creation methods.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from ._indexmanager import IndexManager
from . import interfaces  as search_interfaces
from ._whoosh_content_searcher import wbm_factory
from ._redis_indexmanager import _RedisIndexManager
from . import _cloudsearch_interfaces as cloudsearch_interfaces

def create_index_manager_with_whoosh(indexdir=None, use_md5=True, max_users=100, parallel_search=True):
	content_idx_manager = wbm_factory()
	return IndexManager(content_idx_manager, search_interfaces.IWhooshEntityIndexManager, parallel_search)

def create_index_manager_with_repoze(parallel_search=True):
	content_idx_manager = wbm_factory()
	return IndexManager(content_idx_manager, search_interfaces.IRepozeEntityIndexManager, parallel_search)

def create_index_manager_with_cloudsearch(parallel_search=True):
	content_idx_manager = wbm_factory()
	return _RedisIndexManager(content_idx_manager, cloudsearch_interfaces.ICloudSearchEntityIndexManager, parallel_search)

def create_index_manager_with_repoze_redis(parallel_search=True):
	content_idx_manager = wbm_factory()
	return _RedisIndexManager(content_idx_manager, search_interfaces.IRepozeEntityIndexManager, parallel_search)

create_index_manager = create_index_manager_with_repoze
