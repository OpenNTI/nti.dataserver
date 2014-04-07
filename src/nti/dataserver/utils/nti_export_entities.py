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

from zope import component

from nti.dataserver.users import entity
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization.externalization import toExternalObject

def export_entities(entities, use_profile=False, export_dir=None, verbose=False):
	export_dir = export_dir or os.getcwd()
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	ext = 'txt' if use_profile else 'json'
	utc_datetime = datetime.datetime.utcnow()
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	outname = "entities-%s.%s" % (s, ext)
	outname = os.path.join(export_dir, outname)

	objects = []
	for entityname in entities:
		e = entity.Entity.get_entity(entityname)
		if e is not None:
			to_add = None
			if use_profile and nti_interfaces.IUser.providedBy(e):
				profile = user_interfaces.IUserProfile(e)
				alias = getattr(profile, 'alias', u'')
				email = getattr(profile, 'email', u'')
				realname = getattr(profile, 'realname', u'')
				birthdate = getattr(profile, 'birthdate', u'')
				to_add = (entityname, realname, alias, email, str(birthdate))
			elif not use_profile:
				to_add = toExternalObject(e)
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
					fp.write('\t'.join(o))
					fp.write('\n')

def _process_args(args):
	verbose = args.verbose
	use_profile = args.profile
	export_dir = args.export_dir
	entities = set(args.entities or ())

	if args.all:
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout(dataserver).users_folder
		entities.update(_users.keys())

	if args.site:
		from pyramid.testing import DummyRequest
		from pyramid.testing import setUp as psetUp

		request = DummyRequest()
		config = psetUp(registry=component.getGlobalSiteManager(),
						request=request,
						hook_zca=False)
		config.setup_registry()
		request.headers['origin'] = 'http://' + args.site if not args.site.startswith('http') else args.site
		request.possible_site_names = (args.site if not args.site.startswith('http') else args.site[7:],)

	entities = sorted(entities)
	export_entities(entities, use_profile, export_dir, verbose)

def main():
	arg_parser = argparse.ArgumentParser(description="Export user objects")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('--site', dest='site', help="Application SITE. Use this to get profile info")
	arg_parser.add_argument('--profile', help="Return profile info", action='store_true', dest='profile')
	arg_parser.add_argument('--all', help="Process all entities", action='store_true', dest='all')
	arg_parser.add_argument('entities',
							 nargs="*",
							 help="The entities to process")
	arg_parser.add_argument('-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory")
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	
	conf_packages = () if not args.site else ('nti.appserver',)

	# run export
	run_with_dataserver(environment_dir=env_dir,
						verbose=args.verbose,
						xmlconfig_packages=conf_packages,
						function=lambda: _process_args(args))

if __name__ == '__main__':
	main()
