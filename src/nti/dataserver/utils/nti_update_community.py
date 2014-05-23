#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Update a community

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import pprint
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

def update_community(username, name=None, alias=None, verbose=False):
	__traceback_info__ = locals().items()

	community = users.Community.get_community(username)
	if community is None:
		print("community does not exists", file=sys.stderr)
		sys.exit(2)

	if not nti_interfaces.ICommunity.providedBy(community):
		print("Invalid community", repr(community), file=sys.stderr)
		sys.exit(3)

	if not name and not alias:
		print("Nothing to do", repr(community), file=sys.stderr)
		sys.exit(2)

	ext_value = {}
	if name:
		ext_value['realname'] = name
	if alias:
		ext_value['alias'] = alias

	update_from_external_object(community, ext_value)
	if verbose:
		pprint.pprint(to_external_object(community))

	return community

def process_args(args=None):
	arg_parser = argparse.ArgumentParser(description="Update a community")
	arg_parser.add_argument('username', help="The community to update")
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')

	arg_parser.add_argument('-n', '--name',
							 dest='name',
							 help="The realname of the community")

	arg_parser.add_argument('-a', '--alias',
							 dest='alias',
							 help="The alias of the community")

	arg_parser.add_argument('--site',
							dest='site',
							help="Application SITE.")

	args = arg_parser.parse_args(args=args)

	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError("Invalid dataserver environment root directory", env_dir)
	
	username = args.username
	conf_packages = () if not args.site else ('nti.appserver',)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						function=lambda: update_community(username,
														  args.name,
														  args.alias,
														  args.verbose))
def main(args=None):
	process_args(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
