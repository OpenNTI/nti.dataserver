#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse

from zope import component
from zope.catalog.interfaces import ICatalog

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.users import index as user_index
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

def main():
	arg_parser = argparse.ArgumentParser( description="Return the users that have the opt_in_email_communication set" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-d', '--debug', help="Don't use entity index", action='store_true', dest='debug')
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	verbose = args.verbose
	useindex = not args.debug
	run_with_dataserver( environment_dir=env_dir, function=lambda: _get_user_info(useindex, verbose) )
	sys.exit( 0 )

def _get_user_info(useindex=False, verbose=False):
	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	
	if not useindex:
		dataserver = component.getUtility( nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder
		users = _users.values()
	else:
		users = ent_catalog.searchResults( topics='opt_in_email_communication')
		
	for user in users:
		if not nti_interfaces.IUser.providedBy(user):
			continue
		profile = user_interfaces.ICompleteUserProfile(user)
		if verbose:
			print('\t'.join((user.username, str(profile.opt_in_email_communication), str(profile.email))))
		elif useindex or profile.opt_in_email_communication:
			print('\t'.join((user.username, str(profile.email))))
		
if __name__ == '__main__':
	main()
	