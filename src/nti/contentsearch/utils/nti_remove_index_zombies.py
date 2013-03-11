#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Remove index zombies entries (deleted content)

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import argparse

import zope.intid
from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
from . import find_user_dfls
from ._repoze_utils import get_catalog_and_docids

def _get_object(uid):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	result = _ds_intid.queryObject(uid, None)
	return result
		
def unindex_zombies(entity, verbose=False):
	counter = 0
	for catalog, docids in get_catalog_and_docids(entity):
		for docid in docids:
			if _get_object(docid) is None:
				catalog.unindex_doc(docid)
				counter = counter + 1
	if verbose: 
		print('%s object(s) unindexed for %s' % (counter, entity))
	return counter
			
def remove_zombies(usernames, verbose=False):
	if not usernames:
		dataserver = component.getUtility( nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder
		usernames = _users.iterkeys()

	counter = 0
	for username in usernames:
		entity = users.Entity.get_entity( username )
		if entity is None:
			if verbose:
				print("Entity '%s' could not be found" % username)
			continue
		
		counter += unindex_zombies(entity, verbose)
		if nti_interfaces.IUser.providedBy(entity):
			for dfl in find_user_dfls(entity):
				counter += unindex_zombies(dfl, verbose)
	
	return counter

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
		
if __name__ == '__main__':
	main()
