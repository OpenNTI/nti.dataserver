#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse

from zope import component
from zope.catalog.interfaces import ICatalog

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.users import index as user_index
from nti.dataserver.users import interfaces as user_interfaces

def main():
	arg_parser = argparse.ArgumentParser( description="Return the users that have the opt_in_email_communication set" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	run_with_dataserver( environment_dir=env_dir, function=lambda: _get_user_info() )
	sys.exit( 0 )

def _get_user_info():
	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	ent_catalog.updateIndexes()
	
	for user in list(ent_catalog.searchResults( topics='opt_in_email_communication')):
		profile = user_interfaces.ICompleteUserProfile(user, None)
		if profile is not None:
			print('\t'.join((user.username, profile.email)))
		
if __name__ == '__main__':
	main()
	