#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Index manager creation methods.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import _indexmanager as search_manager
from . import _redis_indexmanager as redis_search_manager

def create_index_manager_with_repoze(parallel_search=True):
	return search_manager.IndexManager(parallel_search)

def create_index_manager_with_repoze_redis(parallel_search=True):
	return redis_search_manager._RedisIndexManager(parallel_search)

create_index_manager = create_index_manager_with_repoze
