#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import pprint
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

def add_remove_friends( owner, name, add_members=(), remove_members=()):
	thelist = None
	flname = name.lower()
	for fl in owner.friendsLists.values():
		if not nti_interfaces.IEntity.providedBy(fl):
			continue
		username = fl.username.lower()
		realname = user_interfaces.IFriendlyNamed( fl ).realname or u''
		if flname == realname.lower() or flname == username:
			thelist = fl
			break

	if thelist is None:
		return None
	
	current_friends = {x for x in thelist}
	to_add = {thelist.get_entity(x) for x in add_members or ()}
	to_add.discard( None )
	to_remove = {thelist.get_entity(x) for x in remove_members or ()}
	to_remove.discard( None )

	final_friends = current_friends | to_add
	final_friends = final_friends - to_remove
	final_friends = {x.username for x in final_friends}
	
	result = update_from_external_object( thelist, {'friends': list(final_friends)} )
	return result

def process_params(args):
	owner = users.User.get_user( args.owner )
	if not owner:
		print("No owner found", args, file=sys.stderr )
		sys.exit( 2 )

	thelist = add_remove_friends(owner, args.name, args.add_members, args.remove_members)
	
	if thelist is None:
		print("Friend list not found", args, file=sys.stderr )
		sys.exit(3)
	
	if args.verbose:
		pprint.pprint( to_external_object( thelist ) )	
	return thelist
		
def main():
	arg_parser = argparse.ArgumentParser( description="Add/Remvove friends from a FriendsList" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'owner', help="The owner of the friend list" )
	arg_parser.add_argument( 'name', help="The name of friend list" )
	arg_parser.add_argument( '-a', '--add',
							 dest='add_members',
							 nargs="+",
							 help="The usernames of the entities to add" )
	arg_parser.add_argument( '-r', '--remove',
							 dest='remove_members',
							 nargs="+",
							 help="The usernames of the entities to remove" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir

	run_with_dataserver( environment_dir=env_dir,
						 verbose=args.verbose,
						 function=lambda: process_params(args) )



if __name__ == '__main__':
	main()
