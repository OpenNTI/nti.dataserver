#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse

from nti.dataserver import users
from nti.dataserver import providers
from nti.dataserver.utils import run_with_dataserver
from nti.contentsearch import interfaces as search_interfaces

_type_map = { 'user': (users.User.get_user, users.User.delete_user),
			  'provider': (providers.Provider.get_entity, providers.Provider.delete_entity),
			  'community': (users.Community.get_entity,  users.Community.delete_entity) }

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

def _remove_user_content( user):
	rim = search_interfaces.IRepozeEntityIndexManager(user)
	for key in list(rim.keys()):
		del rim[key]
			
def _delete_user( factory, username ):
	__traceback_info__ = locals().items()
	getter, deleter = factory
	entity = getter(username)
	if not entity:
		print( "Entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )
	_remove_user_content(entity)
	return deleter(username)

if __name__ == '__main__':
	main()
