#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import

import sys
import argparse
from pprint import pprint

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import to_external_object

from nti.dataserver.utils import run_with_dataserver

def follow_entities(user, follow=()):
	found = set()
	not_found = set()
	member_of = set()
	for username in follow:
		entity = users.Entity.get_entity( username )
		if entity:
			found.add(username)
			user.follow( entity )
			if nti_interfaces.IDynamicSharingTarget(entity):
				user.record_dynamic_membership( entity )
				member_of.add(username)
		else:
			not_found.add(username)

	return (tuple(found), tuple(not_found), tuple(member_of))

def _follow_entities( args ):
	user = users.User.get_user( args.username )
	if not user:
		print( "No user found", args, file=sys.stderr )
		sys.exit( 2 )

	found, not_found, member_of = follow_entities(user, args.follow)
	if args.verbose:
		for n in found:
			print(args.username, "now following", n)

		for n in member_of:
			print(args.username, "now member of", n)

		for n in not_found:
			print("No entity", n, "to follow" )

		pprint( to_external_object( user ) )

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
