# -*- coding: utf-8 -*-
"""
Index manager creation methods.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from ._indexmanager import IndexManager
from . import interfaces  as search_interfaces
from ._whoosh_book_searcher import wbm_factory
from ._redis_indexmanager import _RedisIndexManager
from . import _cloudsearch_interfaces as cloudsearch_interfaces

def create_index_manager_with_whoosh(indexdir=None, use_md5=True, max_users=100):
	book_idx_manager = wbm_factory()
	return IndexManager(book_idx_manager, search_interfaces.IWhooshEntityIndexManager)

def create_index_manager_with_repoze():
	book_idx_manager = wbm_factory()
	return IndexManager(book_idx_manager, search_interfaces.IRepozeEntityIndexManager)

def create_index_manager_with_cloudsearch():
	book_idx_manager = wbm_factory()
	return _RedisIndexManager(book_idx_manager, cloudsearch_interfaces.ICloudSearchEntityIndexManager)

create_index_manager = create_index_manager_with_repoze
