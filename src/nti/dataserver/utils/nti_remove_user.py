#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Remove an entity.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import argparse

from zope import component

from nti.dataserver import users
from nti.dataserver import providers
from nti.dataserver.utils import run_with_dataserver

_type_map = { 'user': (users.User.get_user, users.User.delete_user),
			  'provider': (providers.Provider.get_entity, providers.Provider.delete_entity),
			  'community': (users.Community.get_entity,  users.Community.delete_entity) }

def _delete_user(factory, username, site=None):
	__traceback_info__ = locals().items()

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

	getter, deleter = factory
	entity = getter(username)
	if not entity:
		print("Entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	return deleter(username)

def main():
	arg_parser = argparse.ArgumentParser( description="Delete a user-type object" )
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username to delete")
	arg_parser.add_argument('-t', '--type',
							dest='type',
							choices=_type_map,
							default='user',
							help="The type of user object to delete")
	arg_parser.add_argument('--site',
							dest='site',
							help="Delete the user as if done by a request in this application SITE.")
	args = arg_parser.parse_args()

	site = args.site
	env_dir = args.env_dir
	username = args.username

	run_with_dataserver( environment_dir=env_dir,
						 function=lambda: _delete_user(_type_map[args.type], username, site))
	sys.exit( 0 )

if __name__ == '__main__':
	main()
