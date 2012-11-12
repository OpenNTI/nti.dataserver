#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse

from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

def main():
	arg_parser = argparse.ArgumentParser( description="Return the users that have the opt_in_email_communication set" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	verbose = args.verbose
	run_with_dataserver( environment_dir=env_dir, function=lambda: _get_user_info(verbose) )
	sys.exit( 0 )

def _get_user_info(verbose=False):
	
	dataserver = component.getUtility( nti_interfaces.IDataserver)
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	usernames = _users.iterkeys()

	for username in usernames:
		user = users.User.get_user( username )
		if not user:
			continue
		
		profile = user_interfaces.ICompleteUserProfile(user, None)
		if profile is None and profile.opt_in_email_communication:
			lst = None
			if not verbose:
				lst = [username, profile.email]
			else:
				lst = [username, profile.email, profile.home_page, profile.description]
			
			print('\t'.join(lst))
				
if __name__ == '__main__':
	main()
	