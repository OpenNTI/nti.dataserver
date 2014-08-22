#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Export entity information

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import json
import argparse
import datetime

import zope.intid

from zope import component
from zope.component import hooks

from nti.dataserver.users import Entity
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.users.interfaces import IUserProfile

from nti.externalization.externalization import to_external_object

from zope.catalog.interfaces import ICatalog

from nti.site.site import get_site_for_site_names

def _get_field_value(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = rev_index.get(userid, u'')
	return result

def export_entities(entities, use_profile=False, export_dir=None, verbose=False):
	export_dir = export_dir or os.getcwd()
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	intids = component.getUtility(zope.intid.IIntIds)
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	
	utc_datetime = datetime.datetime.utcnow()
	ext = 'txt' if use_profile else 'json'
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	outname = "entities-%s.%s" % (s, ext)
	outname = os.path.join(export_dir, outname)

	objects = []
	for entityname in entities:
		e = Entity.get_entity(entityname)
		if e is not None:
			to_add = None
			if use_profile and IUser.providedBy(e):
				uid = intids.getId(e)
				alias = _get_field_value(uid, catalog, 'alias')
				email = _get_field_value(uid, catalog, 'email')
				realname = _get_field_value(uid, catalog, 'realname')
				birthdate = getattr(IUserProfile(e), 'birthdate', u'')
				to_add = (entityname, realname, alias, email, str(birthdate))
			elif not use_profile:
				to_add = to_external_object(e)
			if to_add:
				objects.append(to_add)
		elif verbose:
			print("Entity '%s' does not exists" % entityname, file=sys.stderr)

	if objects:
		with open(outname, "w") as fp:
			if not use_profile:
				json.dump(objects, fp, indent=4)
			else:
				for o in objects:
					fp.write('\t'.join(o).encode("utf-8"))
					fp.write('\n')

def _process_args(args):
	verbose = args.verbose
	use_profile = args.profile
	export_dir = args.export_dir
	entities = set(args.entities or ())

	if args.all:
		dataserver = component.getUtility(IDataserver)
		_users = IShardLayout(dataserver).users_folder
		entities.update(_users.keys())

	if args.site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (args.site,), site=cur_site )
		if new_site is cur_site:
			print("Unknown site name", args.site)
			sys.exit(2)
		hooks.setSite(new_site)

	entities = sorted(entities)
	export_entities(entities, use_profile, export_dir, verbose)

def main():
	arg_parser = argparse.ArgumentParser(description="Export user objects")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	arg_parser.add_argument('--site', dest='site', 
							help="Application SITE. Use this to get profile info")
	arg_parser.add_argument('--profile', 
							help="Return profile info", action='store_true',
							dest='profile')
	arg_parser.add_argument('--all', help="Process all entities", action='store_true',
							dest='all')
	arg_parser.add_argument('entities',
							 nargs="*",
							 help="The entities to process")
	arg_parser.add_argument('-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory")
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)
	
	# run export
	run_with_dataserver(environment_dir=env_dir,
						verbose=args.verbose,
						xmlconfig_packages=('nti.appserver',),
						function=lambda: _process_args(args))

if __name__ == '__main__':
	main()
