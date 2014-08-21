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
import argparse

import zope.intid

from zope import component
from zope.component import hooks
from zope.catalog.interfaces import ICatalog

from nti.dataserver.users import Community
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.utils import run_with_dataserver

from nti.site.site import get_site_for_site_names

def _get_field_value(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = rev_index.get(userid, u'')
	return result
			
def get_members(username, site=None, verbose=False):
	__traceback_info__ = locals().items()

	if site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (site,), site=cur_site )
		if new_site is cur_site:
			raise ValueError("Unknown site name", site)
		hooks.setSite(new_site)
	
	community = Community.get_community(username)
	if community is None or not ICommunity.providedBy(community):
		print("Community does not exists", file=sys.stderr)
		sys.exit(2)

	header = ['username', 'realname', 'alias', 'email']
	print('\t'.join(header))
	
	intids = component.getUtility(zope.intid.IIntIds)
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	for user in community:
		if user is not None and IUser.providedBy(user):
			uid = intids.getId(user)
			alias = _get_field_value(uid, catalog, 'alias')
			email = _get_field_value(uid, catalog, 'email')
			realname = _get_field_value(uid, catalog, 'realname')
			print('\t'.join([user.username, realname, alias, email]).encode('utf-8'))

def process_args(args=None):
	arg_parser = argparse.ArgumentParser(description="Return community members")
	arg_parser.add_argument('username', help="The community username")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('--site',
							dest='site',
							help="Application SITE.")
	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError("Invalid dataserver environment root directory", env_dir)

	conf_packages = () if not args.site else ('nti.appserver',)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						function=lambda: get_members(args.username, args.site, args.verbose))
def main(args=None):
	process_args(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
