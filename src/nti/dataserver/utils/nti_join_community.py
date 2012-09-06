#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import sys

from nti.dataserver import users
from nti.externalization.externalization import to_external_object

from . import run_with_dataserver
import argparse

def main():
	arg_parser = argparse.ArgumentParser( description="Join one or more existing communities" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username that should join communities" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '-f', '--follow', help="Also follow the communities", action='store_true', dest='follow')
	arg_parser.add_argument( '-c', '--communities',
							 dest='communities',
							 nargs="+",
							 help="The usernames of the communities to join" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir

	run_with_dataserver( environment_dir=env_dir, function=lambda: _join_community(args) )


def _join_community( args ):
	user = users.User.get_user( args.username )
	if not user:
		print( "No user found", args, file=sys.stderr )
		sys.exit( 2 )

	for com_name in args.communities:
		comm = users.Community.get_entity( com_name )
		if not comm:
			print( "No community found", args, file=sys.stderr )
			sys.exit( 3 )
		user.join_community( comm )
		if args.follow:
			user.follow( comm )

	if args.verbose:
		print( to_external_object( user ) )
	return user
