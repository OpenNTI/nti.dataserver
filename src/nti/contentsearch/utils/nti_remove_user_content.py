#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys

from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from nti.contentsearch.interfaces import IRepozeDataStore
from nti.contentsearch.common import indexable_type_names

def main():
	if len(sys.argv) < 3:
		print( "Usage %s env_dir username *types" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = os.path.expanduser(sys.argv[1])
	username = sys.argv[2]
	idx_types = sys.argv[3:]
	if not idx_types:
		content_types = idx_types
	else:
		content_types = set()
		for tname in idx_types:
			tname = tname.lower()
			if tname in indexable_type_names:
				content_types.append(tname)
		
		if not content_types:
			print("No valid content type(s) were specified")
			sys.exit(2)
			
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: remove_user_content(username) )
			
def remove_user_content( username, indexable_types=indexable_type_names):
	user = users.User.get_user( username )
	if not user:
		print( "user '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 3 )

	# get and register rds
	lsm = component.getSiteManager()
	conn = getattr( lsm, '_p_jar', None )
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	lsm.registerUtility( rds, provided=IRepozeDataStore )

	print('Removing search content object(s) for user', username)

	if indexable_types == indexable_type_names:
		rds.remove_user(username)
	else:
		for tname in indexable_types:
			rds.remove_catalog(username, tname)

if __name__ == '__main__':
	main()
