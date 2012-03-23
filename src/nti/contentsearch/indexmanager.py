import os

from nti.contentsearch._indexmanager import IndexManager
from nti.contentsearch._repoze_datastore import RepozeDataStore
from nti.contentsearch._whoosh_bookindexmanager import wbm_factory
from nti.contentsearch._whoosh_userindexmanager import wuim_factory
from nti.contentsearch._repoze_userindexmanager import ruim_factory
from nti.contentsearch._whoosh_indexstorage import MultiDirectoryStorage
from nti.contentsearch._whoosh_indexstorage import create_zodb_index_storage
from nti.contentsearch._whoosh_indexstorage import create_directory_index_storage

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

def create_index_manager_with_whoosh(index_storage=None, indexdir=None, use_md5=True, dataserver=None):
	book_idx_manager = wbm_factory()
	index_storage = index_storage or MultiDirectoryStorage(indexdir)
	user_idx_manager = wuim_factory(index_storage, use_md5=use_md5)
	return IndexManager(book_idx_manager, user_idx_manager, dataserver=dataserver)

def create_index_manager_with_repoze(search_db=None, dataserver=None, repoze_store=None):
	book_idx_manager = wbm_factory()
	repoze_store = repoze_store or RepozeDataStore(search_db)
	user_idx_manager = ruim_factory(repoze_store)
	return IndexManager(book_idx_manager, user_idx_manager, dataserver=dataserver)

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

def create_zodb_index_manager(	db,
								indicesKey 	= '__indices',
								blobsKey	= "__blobs",
				 				use_lock_file = False,
				 				lock_file_dir = "/tmp/locks",
				 				dataserver = None,
				 				*args, **kwargs):
	"""
	Create a ZODB based index manager.
	
	:param db: zodb database
	:param indicesKey: Entry in root where index names are to be stored
	:param blobsKey: Entry in root where blobs are saved
	:param use_lock_file: flag to use file locks
	:param lock_file_dir: location where file locks will reside
	:param dataserver: Application DataServer (nti.dataserver)
	"""

	logger.info("Creating a zodb based index manager (index=%s, blobs=%s)", indicesKey, blobsKey)

	storage = create_zodb_index_storage(database = db,
										indices_key =indicesKey,
										blobs_key = blobsKey,
										use_lock_file = use_lock_file,
										lock_file_dir = lock_file_dir)

	im = create_index_manager_with_whoosh(storage, dataserver=dataserver)
	return im

# -----------------------------

create_index_manager = create_directory_index_manager
create_repoze_index_manager = create_index_manager_with_repoze
