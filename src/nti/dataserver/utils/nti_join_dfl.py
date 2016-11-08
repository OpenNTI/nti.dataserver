#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Join DFL utility

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from nti.dataserver import users
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.utils import run_with_dataserver

def _process_args(args):
	user = users.User.get_user(args.username)
	if not user or not IUser.providedBy(user):
		print("No user found", args, file=sys.stderr)
		sys.exit(2)

	dfl = users.Entity.get_entity(args.dfl)
	if not dfl or not IDynamicSharingTargetFriendsList.providedBy(user):
		print("No dfl found", args, file=sys.stderr)
		sys.exit(2)

	if not dfl.addFriend(user):
		print('User not added to DFL')
		sys.exit(3)

def main():
	arg_parser = argparse.ArgumentParser(description="Join a DFL")
	arg_parser.add_argument('username', help="The username that should join the DFL")
	arg_parser.add_argument('dfl', help="The DFL NTIID")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory", env_dir)

	run_with_dataserver(environment_dir=env_dir, function=lambda: _process_args(args),
						verbose=args.verbose)

if __name__ == '__main__':
	main()
