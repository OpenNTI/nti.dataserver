#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import codecs
import argparse

import zope.intid

from zope import component

from zope.catalog.interfaces import ICatalog

from nti.common.string import safestr

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users import Community
from nti.dataserver.users.index import CATALOG_NAME

from nti.dataserver.utils import run_with_dataserver

from .base_script import set_site

def _get_field_value(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = safestr(rev_index.get(userid, u''))
	return result

def get_member_info(community):
	intids = component.getUtility(zope.intid.IIntIds)
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	for user in community:
		if not IUser.providedBy(user):
			continue
		uid = intids.getId(user)
		alias = _get_field_value(uid, catalog, 'alias')
		email = _get_field_value(uid, catalog, 'email')
		realname = _get_field_value(uid, catalog, 'realname')
		yield [safestr(user.username), realname, alias, email]

def _output_members(username, tabs=False, output=None, site=None, verbose=False):
	__traceback_info__ = locals().items()

	sep = '\t' if tabs else ','
	if site:
		set_site(site)

	community = Community.get_community(username)
	if community is None or not ICommunity.providedBy(community):
		print("Community does not exists", file=sys.stderr)
		sys.exit(2)

	should_close = output is not None
	output = codecs.open(output, 'w', 'utf-8') \
			 if output else sys.stdout
	header = ['username', 'realname', 'alias', 'email']
	output.write('%s\n' % sep.join(header))

	for row in get_member_info(community):
		__traceback_info__ = row
		try:
			output.write('%s\n' % sep.join(row))
		except UnicodeDecodeError:
			output.write('%r\n' % sep.join(row))

	if should_close:
		output.close()

def process_args(args=None):
	arg_parser = argparse.ArgumentParser(description="Return community members")
	arg_parser.add_argument('username', help="The community username")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-t', '--tabs', help="use tabs as separator",
							action='store_true', dest='tabs')
	arg_parser.add_argument('-o', '--output',
							dest='output',
							help="Output file name.")
	arg_parser.add_argument('--site',
							dest='site',
							help="Application SITE.")
	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=('nti.appserver',),
						verbose=args.verbose,
						function=lambda: _output_members(args.username,
														 args.tabs,
														 args.output,
														 args.site,
														 verbose=args.verbose))
def main(args=None):
	process_args(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
