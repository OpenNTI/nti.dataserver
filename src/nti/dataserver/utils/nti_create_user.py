#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import sys

from nti.dataserver import users
from nti.dataserver import providers
from . import run_with_dataserver

import argparse

_type_map = { 'user': users.User.create_user,
			  'provider': providers.Provider.create_provider }

def main():
	arg_parser = argparse.ArgumentParser( description="Create a user-type object" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to create" )
	arg_parser.add_argument( 'password', nargs='?' )
	arg_parser.add_argument( '-t', '--type',
							 dest='type',
							 choices=_type_map,
							 default='user',
							 help="The type of user object to create" )

	args = arg_parser.parse_args()

	env_dir = args.env_dir
	username = args.username
	password = args.password


	run_with_dataserver( environment_dir=env_dir, function=lambda: _create_user(_type_map[args.type], username, password) )


def _create_user( factory, username, password ):
	user = factory.im_self.get_entity( username )
	if user:
		print( "Not overwriting existing entity", repr(user), file=sys.stderr )
		sys.exit( 2 )

	factory( username=username, password=password )
