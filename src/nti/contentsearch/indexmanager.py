from __future__ import print_function, unicode_literals

import os

from nti.contentsearch._indexmanager import IndexManager
from nti.contentsearch._whoosh_bookindexmanager import wbm_factory
from nti.contentsearch._whoosh_userindexmanager import wuim_factory
from nti.contentsearch._repoze_userindexmanager import ruim_factory
from nti.contentsearch._whoosh_indexstorage import MultiDirectoryStorage
from nti.contentsearch._whoosh_indexstorage import create_directory_index_storage

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

def create_index_manager_with_whoosh(index_storage=None, indexdir=None, use_md5=True, dataserver=None, *args, **kwargs):
	book_idx_manager = wbm_factory()
	index_storage = index_storage or MultiDirectoryStorage(indexdir)
	max_users = kwargs.get('max_users', 100)
	user_idx_manager = wuim_factory(index_storage, max_users=max_users, use_md5=use_md5)
	return IndexManager(book_idx_manager, user_idx_manager)

def create_index_manager_with_repoze(dataserver=None, *args, **kwargs):
	book_idx_manager = wbm_factory()
	user_idx_manager = ruim_factory()
	return IndexManager(book_idx_manager, user_idx_manager)

# -----------------------------

def create_directory_index_manager(user_index_dir="/tmp",  use_md5=True, dataserver=None, *args, **kwargs):
	"""
	Create a directory based index manager"
	
	:param user_index_dir: location of user indices
	:param use_md5: flag to md5 has the indices names
	"""
	
	logger.info("Creating a directory based index manager '%s'", user_index_dir)
	
	if user_index_dir == '/tmp' and 'DATASERVER_DIR' in os.environ:
		user_index_dir = os.environ['DATASERVER_DIR']
		
	storage = create_directory_index_storage(user_index_dir)
	im = create_index_manager_with_whoosh(storage, use_md5=use_md5, dataserver=dataserver)
	return im

# -----------------------------

create_index_manager = create_directory_index_manager
create_repoze_index_manager = create_index_manager_with_repoze
