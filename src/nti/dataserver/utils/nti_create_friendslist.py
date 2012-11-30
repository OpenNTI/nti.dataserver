#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import pprint
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object

def create_friends_list(owner, username, realname=None, members=(), dynamic=False ):
	factory = users.DynamicFriendsList if dynamic else users.FriendsList
	dfl = factory( username=unicode(username) )
	dfl.creator = owner
	if realname:
		user_interfaces.IFriendlyNamed( dfl ).realname = unicode(realname)
	
	# add to container b4 adding members
	owner.addContainedObject( dfl )
	
	for member_name in members or ():
		member = users.User.get_user( member_name )
		if member and member != owner:
			dfl.addFriend( member )

	return dfl

def _create_fl( args ):
	owner = users.User.get_user( args.owner )
	if not owner:
		print( "No owner found", args, file=sys.stderr )
		sys.exit( 2 )

	fl = create_friends_list(owner, args.username, args.name, args.members, args.dynamic)
	if args.verbose:
		pprint.pprint( to_external_object( fl ) )
		
	return fl

def main():
	arg_parser = argparse.ArgumentParser( description="Create a (Dynamic)FriendsList" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'owner', help="The username of the owner" )
	arg_parser.add_argument( 'username', help="The username of the new DFL" )
	arg_parser.add_argument( '-n', '--name',
							 dest='name',
							 help="The display name of the list" )
	arg_parser.add_argument( '--dynamic',
							 help="Create a Dynamic FriendsList",
							 action='store_true',
							 dest='dynamic' )
	arg_parser.add_argument( '-m', '--members',
							 dest='members',
							 nargs="+",
							 help="The usernames of the entities to add; must already exist" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir

	run_with_dataserver( environment_dir=env_dir,
						 verbose=args.verbose,
						 function=lambda: _create_fl(args) )

if __name__ == '__main__':
	main()
	