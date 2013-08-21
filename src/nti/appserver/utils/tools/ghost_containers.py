#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Store admin views

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import argparse

from zope import interface
from zope import component

from nti.contentmanagement import get_collection_root

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

exclude_containers = (u'Devices', u'FriendsLists', u'')

def _check_users(usernames=(), args=(), options=None):
	__traceback_info__ = locals().items()

	if usernames:
		_users = {users.User.get_entity(x) for x in usernames}
		_users.discard(None)
	else:
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout(dataserver).users_folder
		_users = _users.values()
	
	result = {}
	for user in _users:
		method = getattr(user, 'getAllContainers', lambda : ())
		usermap = {}
		for name in method():
			if get_collection_root(name) is None:
				container = user.getContainer(name)
				usermap[name] = len(container) if container is not None else 0
			print(type(container))
	
	return result

def main(args=None):
	arg_parser = argparse.ArgumentParser(description="Create a user-type object")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('-u', '--users',
							 dest='users',
							 nargs="+",
							 default=(),
							 help="The names of users to check")

	args = arg_parser.parse_args(args=args)

	env_dir = args.env_dir
	usernames = args.usernames

	conf_packages = ('nti.appserver',)
	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						function=lambda: _check_users(usernames, args))
	sys.exit(0)
