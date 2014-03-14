#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Join community utility

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import pprint
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import to_external_object

def join_communities(user, communities=(), follow=False, exitOnError=False):
	not_found = set()
	for com_name in communities:
		comm = users.Community.get_entity(com_name)
		if not comm or not nti_interfaces.ICommunity.providedBy(comm):
			not_found.add(com_name)
			if exitOnError:
				break
		else:
			user.record_dynamic_membership(comm)
			if follow:
				user.follow(comm)

	return tuple(not_found)

def _process_args(args):
	user = users.User.get_user(args.username)
	if not user or not nti_interfaces.IUser.providedBy(user):
		print("No user found", args, file=sys.stderr)
		sys.exit(2)

	not_found = join_communities(user, args.communities, args.follow, True)
	if not_found:
		print("No community found", args, file=sys.stderr)
		sys.exit(3)

	if args.verbose:
		pprint.pprint(to_external_object(user))

def main():
	arg_parser = argparse.ArgumentParser( description="Join one or more existing communities" )
	arg_parser.add_argument('username', help="The username that should join communities")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('-f', '--follow', help="Also follow the communities", action='store_true', dest='follow')
	arg_parser.add_argument('-c', '--communities',
							dest='communities',
							nargs="+",
							help="The usernames of the communities to join")
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	args = arg_parser.parse_args()

	import os
	
	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	
	run_with_dataserver( environment_dir=env_dir, function=lambda: _process_args(args) )

if __name__ == '__main__':
	main()

