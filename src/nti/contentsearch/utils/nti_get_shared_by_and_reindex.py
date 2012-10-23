#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import six
import sys
import argparse

from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.activitystream_change import Change

import nti.contentsearch
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.utils.nti_reindex_user_content import reindex_entity_content

def main():
	arg_parser = argparse.ArgumentParser( description="Print names of entities that could share with a particular user" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username" )
	arg_parser.add_argument( '--verbose', help="Unindex content in user's dfls", action='store_true', dest='verbose')
	arg_parser.add_argument( '--reindex', help="Verbose output", action='store_true', dest='reindex')
	args = arg_parser.parse_args()

	verbose = args.verbose
	reindex = args.reindex
	username = args.username
	env_dir = os.path.expanduser(args.env_dir)
	
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: compute_shared_by_and_reindex(username, reindex, verbose) )
	
def get_creator(obj):
	creator = None
	if hasattr(obj, 'creator'):
		creator = obj.creator
	else:
		adapted = component.queryAdapter(obj, search_interfaces.IContentResolver)
		creator = getattr(adapted, 'get_creator', None) if adapted is not None else None
		creator = creator() if creator else None
		
	creator = creator.username if creator and hasattr(creator, 'username') else creator
	return creator
		
def compute_shared_by_and_reindex(username, reindex, verbose):
	entity = users.Entity.get_entity( username )
	if not entity:
		print( "user/entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit(2)

	communities_dfls = list(entity.communities) if entity and hasattr(entity, 'communities') else ()
	if communities_dfls and 'Everyone' in communities_dfls:
		communities_dfls.remove('Everyone')
		
	result = set()
	
	# check in my stream	
	def _process_change(c):
		if isinstance(c, Change) and c.type != Change.CIRCLED:
			creator = c.creator.username if hasattr(c.creator, 'username') else c.creator
			result.add(creator)
	
	for s in entity.streamCache:
		if isinstance(s, six.string_types):
			for c in entity.getContainedStream(s):
				_process_change(c)
		else:
			_process_change(c)
	
	# check in things shared directly with me
	for container in entity.containersOfShared.containers.values():
		for obj in container:
			creator = get_creator(obj)
			if creator: result.add(creator)
				
	result.update(communities_dfls)
	if username in result:
		result.remove(username)
	result = sorted(result)
	
	if not reindex:
		for u in result:
			print(u)
	else:
		if verbose:
			print('Reindexing data for %s entities\n' % len(result))
		for u in result:
			if users.Entity.get_entity(u) is not None:
				reindex_entity_content(u, include_dfls=True, verbose=verbose)
			elif verbose:
				print('%s was not found' % u)
	
	return result
	
if __name__ == '__main__':
	main()
