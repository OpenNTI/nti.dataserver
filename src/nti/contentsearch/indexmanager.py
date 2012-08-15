from __future__ import print_function, unicode_literals

from nti.contentsearch._indexmanager import IndexManager
from nti.contentsearch import interfaces  as search_interfaces
from nti.contentsearch._whoosh_bookindexmanager import wbm_factory

import logging
logger = logging.getLogger( __name__ )

def create_index_manager_with_whoosh(indexdir=None, use_md5=True, max_users=100):
	book_idx_manager = wbm_factory()
	return IndexManager(book_idx_manager, search_interfaces.IWhooshEntityIndexManager)

def create_index_manager_with_cloudsearch():
	book_idx_manager = wbm_factory()
	return IndexManager(book_idx_manager, search_interfaces.ICloudSearchEntityIndexManager)

def create_index_manager_with_repoze():
	book_idx_manager = wbm_factory()
	return IndexManager(book_idx_manager, search_interfaces.IRepozeEntityIndexManager)


