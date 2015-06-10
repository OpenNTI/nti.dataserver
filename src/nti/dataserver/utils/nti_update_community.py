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

from nti.dataserver.users import Community
from nti.dataserver.interfaces import ICommunity

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from . import run_with_dataserver

def update_community(username, name=None, alias=None, public=False,
					 joinable=False, verbose=False):
	__traceback_info__ = locals().items()

	if alias and not isinstance(alias, unicode):
		alias = unicode(alias.decode("UTF-8"))

	if name and not isinstance(name, unicode):
		name = unicode(name.decode("UTF-8"))

	community = Community.get_community(username)
	if community is None:
		print("community does not exists", file=sys.stderr)
		sys.exit(2)

	if not ICommunity.providedBy(community):
		print("Invalid community", repr(community), file=sys.stderr)
		sys.exit(3)

	ext_value = {}
	if name:
		ext_value['realname'] = name
	if alias:
		ext_value['alias'] = alias

	if community.public != public:
		ext_value['public'] = public
	if community.joinable != joinable:
		ext_value['joinable'] = joinable

	if not ext_value:
		print("Nothing to do", repr(community), file=sys.stderr)
		sys.exit(0)
		
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

	arg_parser.add_argument('--public',
							 dest='public',
							 action='store_true',
							 default=False,
							 help="Public community")

	arg_parser.add_argument('--joinable',
							 dest='joinable',
							 action='store_true',
							 default=False,
							 help="Joinable community")

	arg_parser.add_argument('--site',
							dest='site',
							help="Application SITE.")

	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory", env_dir)

	username = args.username
	conf_packages = () if not args.site else ('nti.appserver',)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						function=lambda: update_community(username,
														  args.name,
														  args.alias,
														  args.public,
														  args.joinable,
														  args.verbose))
def main(args=None):
	process_args(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
