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
import csv
import sys
import json
import argparse
from datetime import datetime

import zope.intid
import zope.browserpage

from zope import component
from zope.component import hooks
from zope.catalog.interfaces import ICatalog
from zope.container.contained import Contained
from zope.configuration import xmlconfig, config
from zope.dottedname import resolve as dottedname

from z3c.autoinclude.zcml import includePluginsDirective

from nti.dataserver.users import Entity
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.users.interfaces import IUserProfile

from nti.externalization.externalization import to_external_object

from nti.site.site import get_site_for_site_names

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

def _tx_string(s):
	if s and isinstance(s, unicode):
		s = s.encode('utf-8')
	return s

def _parse_time(t):
	try:
		return datetime.fromtimestamp(t).isoformat() if t else u''
	except ValueError:
		logger.debug("Cannot parse time '%s'" % t)
		return str(t)
	
def get_index_field_value(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = rev_index.get(userid, u'')
	return result

def export_entities(entities, full=False, as_csv=False, 
					export_dir=None, verbose=False):
	export_dir = export_dir or os.getcwd()
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	intids = component.getUtility(zope.intid.IIntIds)
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	
	utc_datetime = datetime.utcnow()
	ext = 'csv' if as_csv else 'json'
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	outname = "entities-%s.%s" % (s, ext)
	outname = os.path.join(export_dir, outname)

	objects = []
	for entityname in entities:
		e = Entity.get_entity(entityname)
		if e is None:
			if verbose:
				print("Entity '%s' does not exists" % entityname, file=sys.stderr)
			continue

		to_add = None
		if as_csv and IUser.providedBy(e):
			uid = intids.getId(e)
			alias = get_index_field_value(uid, catalog, 'alias')
			email = get_index_field_value(uid, catalog, 'email')
			birthdate = getattr(IUserProfile(e), 'birthdate', u'')
			realname = get_index_field_value(uid, catalog, 'realname')
			createdTime = _parse_time(getattr(e, 'createdTime', 0))
			lastLoginTime = _parse_time(getattr(e, 'lastLoginTime', None))
			to_add = [entityname, realname, alias, email, createdTime, 
					  lastLoginTime, str(birthdate) if birthdate else None]
		elif not as_csv:
			if full:
				to_add = to_external_object(e)
			else:
				to_add = to_external_object(e, name="summary")
		if to_add:
			objects.append(to_add)

	with open(outname, "w") as fp:
		if not as_csv:
			json.dump(objects, fp, indent=4)
		else:
			writer = csv.writer(fp)
			writer.writerow(['username', 'realname', 'alias', 'email', 'createdTime',
							 'lastLoginTime', 'birthdate'])
			for o in objects:
				writer.writerow([_tx_string(x) for x in o])
					
	if verbose:
		print(len(objects), " entities outputed to ", outname)

def _create_context(env_dir):
	etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
	etc = os.path.expanduser(etc)

	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)
		
	slugs = os.path.join(etc, 'package-includes')
	if os.path.exists(slugs) and os.path.isdir(slugs):
		package = dottedname.resolve('nti.dataserver')
		context = xmlconfig.file('configure.zcml', package=package, context=context)
		xmlconfig.include(context, files=os.path.join(slugs, '*.zcml'),
						  package='nti.appserver')

	library_zcml = os.path.join(etc, 'library.zcml')
	if os.path.exists(library_zcml):
		xmlconfig.include(context, file=library_zcml)
	else:
		logger.warn("Library not loaded")
	
	# Include zope.browserpage.meta.zcm for tales:expressiontype
	# before including the products
	xmlconfig.include(context, file="meta.zcml", package=zope.browserpage)

	# include plugins
	includePluginsDirective(context, PP_APP)
	includePluginsDirective(context, PP_APP_SITES)
	includePluginsDirective(context, PP_APP_PRODUCTS)
	
	return context

def _process_args(args):
	full = args.full
	as_csv = args.as_csv
	verbose = args.verbose
	export_dir = args.export_dir
	
	if args.all:
		dataserver = component.getUtility(IDataserver)
		users_folder = IShardLayout(dataserver).users_folder
		entities = users_folder.keys()
	else:
		entities = set(args.entities or ())

	if args.site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (args.site,), site=cur_site )
		if new_site is cur_site:
			print("Unknown site name", args.site)
			sys.exit(2)
		hooks.setSite(new_site)

	entities = sorted(entities)
	export_entities(entities, full, as_csv, export_dir, verbose)

def main():
	arg_parser = argparse.ArgumentParser(description="Export user objects")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	arg_parser.add_argument('--site', dest='site', 
							help="Application SITE.")
	arg_parser.add_argument('--all', help="Process all entities",
							action='store_true',
							dest='all')
	arg_parser.add_argument('entities',
							 nargs="*",
							 help="The entities to process")
	arg_parser.add_argument('-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory")
	site_group = arg_parser.add_mutually_exclusive_group()
	site_group.add_argument('--full',
							 dest='full',
							 help="Use full externalizer")
	site_group.add_argument('--csv', 
							help="Output CSV", action='store_true',
							dest='as_csv')
	
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)
	
	context = _create_context(env_dir)
	conf_packages = ('nti.appserver',)
	
	# run export
	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						context=context,
						function=lambda: _process_args(args))

if __name__ == '__main__':
	main()
