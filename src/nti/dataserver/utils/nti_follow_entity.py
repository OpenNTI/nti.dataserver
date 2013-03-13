#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import

import sys
import argparse
from pprint import pprint

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import to_external_object

from nti.dataserver.utils import run_with_dataserver

def _follow_entities(user, to_follow=(), follow=None, record=None, addFriend=None):
	found = set()
	not_found = set()
	member_of = set()
	for username in to_follow:
		entity = users.Entity.get_entity( username )
		if entity:
			found.add(username)
			follow( user, entity )

			if nti_interfaces.IDynamicSharingTarget(entity):
				record( user, entity )
				addFriend( entity, user )

				member_of.add(username)
		else:
			not_found.add(username)

	return found, not_found, member_of

def follow_entities(user, to_follow=()):
	def follow(user, entity):
		user.follow( entity )
	def record(user, entity ):
		user.record_dynamic_membership( entity )
	def add(entity, user):
		if hasattr( entity, 'addFriend' ):
			entity.addFriend( user )

	return _follow_entities( user, to_follow=to_follow, follow=follow, record=record, addFriend=add )


def unfollow_entities(user, to_follow=()):
	def follow(user, entity):
		user.stop_following( entity )
	def record(user, entity ):
		user.record_no_longer_dynamic_member( entity )
	def add(entity, user):
		if hasattr( entity, 'removeFriend' ):
			entity.removeFriend( user )

	return _follow_entities( user, to_follow=to_follow, follow=follow, record=record, addFriend=add )

def _action( args ):
	user = users.User.get_user( args.username )
	if not user:
		print( "No user found", args, file=sys.stderr )
		sys.exit( 2 )

	if args.unfollow:
		found, not_found, member_of = unfollow_entities(user, args.follow)
	else:
		found, not_found, member_of = follow_entities(user, args.follow)
	if args.verbose:
		now = "now"
		follow = "follow"
		if args.unfollow:
			now = "no longer"
			follow = "unfollow"

		for n in found:
			print(args.username, now + " following", n)

		for n in member_of:
			print(args.username, now + " member of", n)

		for n in not_found:
			print("No entity", n, "to " + follow )

		pprint( to_external_object( user ) )

def main():
	arg_parser = argparse.ArgumentParser( description="Make a user (un)follow an existing entity; if a DynamicSharingTarget, they also join it." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to edit" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '-x', '--unfollow', help="Unfollow instead of follow", action='store_true', dest='unfollow')
	arg_parser.add_argument( '-f', '--follow',
							 dest='follow',
							 nargs="+",
							 required=True,
							 help="The usernames of the entities to (un)follow" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir

	run_with_dataserver( environment_dir=env_dir, function=lambda: _action(args) )
