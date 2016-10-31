#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import pprint
import argparse

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import create_context

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

def add_remove_friends(owner, name, add_members=(), remove_members=()):
	thelist = None
	flname = name.lower()
	for fl in getattr(owner, 'getFriendsLists', lambda s: ())(owner):
		if not IEntity.providedBy(fl):
			continue
		username = fl.username.lower()
		realname = IFriendlyNamed(fl).realname or u''
		if flname == realname.lower() or flname == username:
			thelist = fl
			break

	if thelist is None:
		return None

	current_friends = {x for x in thelist}
	to_add = {thelist.get_entity(x) for x in add_members or ()}
	to_add.discard(None)

	to_remove = {thelist.get_entity(x) for x in remove_members or ()}
	to_remove.discard(None)

	final_friends = current_friends | to_add
	final_friends = final_friends - to_remove
	final_friends = {x.username for x in final_friends}

	result = update_from_external_object(thelist, {'friends': list(final_friends)})
	return result

def process_params(args):
	owner = User.get_user(args.owner)
	if not owner or not IUser.providedBy(owner):
		print("No owner found", args, file=sys.stderr)
		sys.exit(2)

	thelist = add_remove_friends(owner, args.name,
								 args.add_members,
								 args.remove_members)

	if thelist is None:
		print("Friend list not found", args, file=sys.stderr)
		sys.exit(3)

	if args.verbose:
		pprint.pprint(to_external_object(thelist))
	return thelist

def main():
	arg_parser = argparse.ArgumentParser(description="Add/Remvove friends from a FriendsList")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('owner', help="The owner of the friend list")
	arg_parser.add_argument('name', help="The name of friend list")
	arg_parser.add_argument('-a', '--add',
							dest='add_members',
							nargs="+",
							help="The usernames of the entities to add")
	arg_parser.add_argument('-r', '--remove',
							dest='remove_members',
							nargs="+",
							help="The usernames of the entities to remove")
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError("Invalid dataserver environment root directory", env_dir)

	conf_packages = ('nti.appserver',)
	context = create_context(env_dir, with_library=True)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						context=context,
						function=lambda: process_params(args))

if __name__ == '__main__':
	main()
