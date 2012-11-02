#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import time
import argparse

from ZODB.POSException import POSKeyError

from nti.dataserver import users
from nti.dataserver.users import friends_lists
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from nti.contentsearch.utils import get_uid
from nti.contentsearch.utils import find_all_indexable_pairs
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.utils._repoze_utils import remove_entity_catalogs
			
def reindex_entity_content(username, include_dfls=False, verbose=False):
	entity = users.Entity.get_entity( username )
	if not entity:
		print( "user/entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	counter = 0	
	dfl_names = set()
	
	t = time.time()
		
	# remove catalogs for main entity
	remove_entity_catalogs(entity)
	
	# loop through all user indexable objects
	for e, obj in find_all_indexable_pairs(entity, include_dfls=include_dfls):
		
		# if we find a DFL clear its catalogs
		if isinstance(e, friends_lists.DynamicFriendsList) and e.username not in dfl_names:
			remove_entity_catalogs(e)
			dfl_names.add(e.username)
		
		rim = search_interfaces.IRepozeEntityIndexManager(e, None)
		try:
			catalog = rim.get_create_catalog(obj) if rim is not None else None
			if catalog is not None:
				docid = get_uid(obj)
				if docid is not None:
					catalog.index_doc(docid, obj)
					counter = counter + 1
				elif verbose:
					print("Cannot find int64 id for %r. Object will not be indexed" % obj)
		except POSKeyError:
			# broken reference for object
			pass
	
	t = time.time() - t
	if verbose:
		print('%s object(s) reindexed for %s in %.2f(s)' % (counter, username, t))
		
	return counter

def main():
	arg_parser = argparse.ArgumentParser( description="Reindex user content" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username" )
	arg_parser.add_argument( '--include_dfls', help="Unindex content in user's dfls", action='store_true', dest='include_dfls')
	arg_parser.add_argument( '--verbose', help="Verbose output", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	include_dfls = args.include_dfls
	env_dir = os.path.expanduser(args.env_dir)
	
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: reindex_entity_content(username, include_dfls, verbose) )

if __name__ == '__main__':
	main()
