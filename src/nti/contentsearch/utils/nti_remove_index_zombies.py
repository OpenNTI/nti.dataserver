#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import argparse

import zope.intid
from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
from nti.contentsearch import interfaces as search_interfaces

def main():
	arg_parser = argparse.ArgumentParser( description="Remove index zombies" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( 'usernames',
							 nargs="*",
							 help="The username(s) to process" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	usernames = args.usernames
	verbose = args.verbose
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: remove_zombies(usernames, verbose) )
		

def _get_object(uid):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	result = _ds_intid.queryObject(uid, None)
	return result

def _get_docids_from_catalog_field(catfield):
	m = getattr(catfield, "_indexed", None)
	result = list(catfield._indexed()) if m is not None else ()
	return result	
		
def _get_docids_from_rim(rim):
	for catalog in rim.values():
		for catfield in catalog.values():
			yield catalog, _get_docids_from_catalog_field(catfield)
			break
			
def remove_zombies( usernames, verbose=False):
	
	if not usernames:
		dataserver = component.getUtility( nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder
		usernames = _users.iterkeys()
	

	for username in usernames:
		entity = users.Entity.get_entity( username )
		if entity is None or nti_interfaces.IFriendsList.providedBy(entity):
			continue
		
		rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if rim is not None:
			counter = 0
			for catalog, docids in _get_docids_from_rim(rim):
				for docid in docids:
					if _get_object(docid) is None:
						catalog.unindex_doc(docid)
						counter = counter + 1
			if verbose: print('%s object(s) unindexed for %s' % (counter, username))

if __name__ == '__main__':
	main()
