#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Creates a friend list

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import sys
import pprint
import argparse

from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization.externalization import to_external_object

def create_friends_list(owner, username, realname=None, members=(), dynamic=False,
						locked=False):

	factory = users.DynamicFriendsList if dynamic else users.FriendsList
	dfl = factory(username=unicode(username))
	dfl.creator = owner
	if dynamic:
		dfl.Locked = locked
	if realname:
		user_interfaces.IFriendlyNamed( dfl ).realname = unicode(realname)

	# add to container b4 adding members
	owner.addContainedObject( dfl )

	for member_name in members or ():
		member = users.User.get_user( member_name )
		if member and member != owner:
			dfl.addFriend( member )

	return dfl

def _process_args(args):
	owner = users.User.get_user(args.owner)
	if not owner or not nti_interfaces.IUser.providedBy(owner):
		print( "No owner found", args, file=sys.stderr )
		sys.exit( 2 )

	site = args.site
	if site:
		from pyramid.testing import DummyRequest
		from pyramid.testing import setUp as psetUp

		request = DummyRequest()
		config = psetUp(registry=component.getGlobalSiteManager(),
						request=request,
						hook_zca=False)
		config.setup_registry()
		request.headers['origin'] = 'http://' + site if not site.startswith('http') else site
		request.possible_site_names = (site if not site.startswith('http') else site[7:],)

	result = create_friends_list(owner, args.username, args.name, args.members,
								 args.dynamic, args.locked)
	if args.verbose:
		pprint.pprint(to_external_object(result))
	return result

def main():
	arg_parser = argparse.ArgumentParser(description="Create a [Dynamic]FriendsList")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('owner', help="The username of the owner")
	arg_parser.add_argument('username', help="The username of the new DFL")
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('-n', '--name',
							dest='name',
							help="The display name of the list")
	arg_parser.add_argument('--dynamic',
							help="Create a Dynamic FriendsList",
							action='store_true',
							dest='dynamic')
	arg_parser.add_argument('--locked',
							help="Lock the DFL. Only valid used with --dynamic",
							action='store_true',
							dest='locked')
	arg_parser.add_argument('--site',
							dest='site',
							help="Request SITE.")
	arg_parser.add_argument('-m', '--members',
							dest='members',
							nargs="+",
							help="The usernames of the entities to add; must already exist")
	args = arg_parser.parse_args()

	import os
	
	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	
	run_with_dataserver( environment_dir=env_dir,
						 verbose=args.verbose,
						 function=lambda: _process_args(args))
	sys.exit(0)

if __name__ == '__main__':
	main()
