#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from nti.contentsearch import get_indexable_types
from nti.contentsearch.utils import find_user_dfls
from nti.contentsearch.common import normalize_type_name as _nrm
from nti.contentsearch.utils.repoze_utils import remove_entity_catalogs

def main():
	arg_parser = argparse.ArgumentParser( description="Unindex user content" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username" )
	arg_parser.add_argument( '--include_dfls', help="Unindex content in user's dfls", action='store_true', dest='include_dfls')
	arg_parser.add_argument( '-t', '--types',
							 nargs="*",
							 dest='idx_types',
							 help="The content type(s) to unindex" )
	args = arg_parser.parse_args()

	username = args.username
	idx_types = args.idx_types
	include_dfls = args.include_dfls
	env_dir = os.path.expanduser(args.env_dir)
	if not idx_types:
		content_types = get_indexable_types()
	else:
		content_types = [_nrm(n) for n in idx_types if _nrm(n) in get_indexable_types()]
		content_types = set(content_types)
		if not content_types:
			print("No valid content type(s) were specified")
			sys.exit(3)
			
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: remove_user_content(username, content_types, include_dfls) )
			
def remove_entity_content(username, content_types=(), include_dfls=False):
	entity = users.Entity.get_entity( username )
	if not entity:
		print( "user/entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit(2)

	remove_entity_catalogs(username, content_types)
	if include_dfls:
		for dfl in find_user_dfls(entity):
			remove_entity_catalogs(dfl, content_types)

remove_user_content = remove_entity_content

if __name__ == '__main__':
	main()
