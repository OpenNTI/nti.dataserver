#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Remove an entity.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from zope.component import hooks

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.site.site import get_site_for_site_names

_type_map = { 'user': (users.User.get_user, users.User.delete_user),
			  'community': (users.Community.get_entity,  users.Community.delete_entity) }

def _delete_user(factory, username, site=None):
	__traceback_info__ = locals().items()

	if site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (site,), site=cur_site )
		if new_site is cur_site:
			raise ValueError("Unknown site name", site)

		hooks.setSite(new_site)


	getter, deleter = factory
	entity = getter(username)
	if not entity:
		print("Entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	return deleter(username)

def main():
	arg_parser = argparse.ArgumentParser( description="Delete a user-type object" )
	arg_parser.add_argument('username', help="The username to delete")
	arg_parser.add_argument('-t', '--type',
							dest='type',
							choices=_type_map,
							default='user',
							help="The type of user object to delete")
	arg_parser.add_argument('--site',
							dest='site',
							help="Delete the user as if done by a request in this application SITE.")
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	args = arg_parser.parse_args()

	site = args.site

	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )

	username = args.username

	run_with_dataserver( environment_dir=env_dir,
						 # MUST be sure to get the site configurations
						 # loaded.
						 xmlconfig_packages=('nti.appserver',),
						 function=lambda: _delete_user(_type_map[args.type], username, site))
	sys.exit( 0 )

if __name__ == '__main__':
	main()
