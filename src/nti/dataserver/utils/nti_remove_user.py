#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys

from nti.dataserver import users
from nti.dataserver import providers
from nti.dataserver.utils import run_with_dataserver

import argparse

_type_map = { 'user': users.User.create_user,
			  'provider': providers.Provider.create_provider,
			  'community': users.Community.create_community }

def main():
	arg_parser = argparse.ArgumentParser( description="Delete a user-type object" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to delete" )
	arg_parser.add_argument( '-t', '--type',
							 dest='type',
							 choices=_type_map,
							 default='user',
							 help="The type of user object to delete" )

	args = arg_parser.parse_args()

	env_dir = args.env_dir
	username = args.username

	run_with_dataserver( environment_dir=env_dir,
						 function=lambda: _delete_user(_type_map[args.type], username ) )
	sys.exit( 0 )

def _delete_user( factory, username ):
	__traceback_info__ = locals().items()
	user = factory.get_entity(username)
	if not user:
		print( "User does not exists", repr(user), file=sys.stderr )
		sys.exit(-2)
	factory.im_self.delete_entity( username )
	
if __name__ == '__main__':
	main()