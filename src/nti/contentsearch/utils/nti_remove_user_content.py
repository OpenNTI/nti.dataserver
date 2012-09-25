#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from nti.contentsearch import get_indexable_types
from nti.contentsearch import interfaces as search_interfaces

def main():
	if len(sys.argv) < 3:
		print( "Usage %s env_dir username *types" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = os.path.expanduser(sys.argv[1])
	username = sys.argv[2]
	idx_types = sys.argv[3:]
	if not idx_types:
		content_types = get_indexable_types()
	else:
		content_types = set()
		for tname in idx_types:
			tname = tname.lower()
			if tname in get_indexable_types():
				content_types.append(tname)
		
		if not content_types:
			print("No valid content type(s) were specified")
			sys.exit(2)
			
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: remove_user_content(username, content_types) )
			
def remove_entity_content( username, content_types):
	entity = users.Entity.get_entity( username )
	if not entity:
		print( "user/entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 3 )

	rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
	if rim is not None:
		for key in list(rim.keys()):
			if key in content_types:
				rim.pop(key, None)

remove_user_content = remove_entity_content

if __name__ == '__main__':
	main()
