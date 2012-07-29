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
	arg_parser = argparse.ArgumentParser( description="Make a user follow an existing entity; if a community, they also join the community." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to edit" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '-f', '--follow',
							 dest='follow',
							 nargs="+",
							 required=True,
							 help="The usernames of the entities to follow" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir


	run_with_dataserver( environment_dir=env_dir, function=lambda: _follow_entities(args) )


def _follow_entities( args ):
	user = users.User.get_user( args.username )
	if not user:
		print( "No user found", args, file=sys.stderr )
		sys.exit( 2 )

	for username in args.follow:
		entity = users.Entity.get_entity( username )
		if entity:
			if args.verbose:
				print( args.username, "now following", username )
			user.follow( entity )
			if isinstance( entity, users.Community ):
				user.join_community( entity )
				if args.verbose:
					print( args.username, "now member of community", username )
		elif args.verbose:
			print( "No entity", username, "to follow" )

	if args.verbose:
		print( to_external_object( user ) )
