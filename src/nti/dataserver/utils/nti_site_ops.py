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
from collections import Mapping

import zope.browserpage

from zope import component
from zope.container.contained import Contained
from zope.configuration import xmlconfig, config
from zope.dottedname import resolve as dottedname
from zope.traversing.interfaces import IEtcNamespace
from zope.component.hooks import site as current_site

from z3c.autoinclude.zcml import includePluginsDirective

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.utils import run_with_dataserver

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

conf_package = 'nti.appserver'

def list_sites():
	sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
	for name, site in sites_folder.items():
		print("Site:",  name)
		for k,v in site.items():
			print("\t", k, v)
	
def remove_site(name, verbose=True, library=True):
	if library:
		pack_lib = component.queryUtility(IContentPackageLibrary)
		getattr(pack_lib, 'contentPackages', None)		
	sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
	del sites_folder[name]
	if verbose:
		print('Site ' + name + ' removed')
		
def info_site(name):
	
	def _print(key, value, tabs=1):
		s = '\t' * tabs
		print(s, key, value)
		if isinstance(value, Mapping):
			for k, v  in value.items():
				_print(k, v, tabs+1)
				
	sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
	local_site = sites_folder[name]
	with current_site(local_site):
		manager = local_site.getSiteManager()
		print("Site:", name)
		print("\tManager:", manager.__name__, manager)
		for key, value in manager.items():
			_print(key, value, 2)
		
def create_context(env_dir):
	etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
	etc = os.path.expanduser(etc)

	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)

	slugs = os.path.join(etc, 'package-includes')
	if os.path.exists(slugs) and os.path.isdir(slugs):
		package = dottedname.resolve('nti.dataserver')
		context = xmlconfig.file('configure.zcml', package=package, context=context)
		xmlconfig.include(context, files=os.path.join(slugs, '*.zcml'),
						  package=conf_package)

	library_zcml = os.path.join(etc, 'library.zcml')
	if not os.path.exists(library_zcml):
		raise Exception("Could not locate library zcml file %s", library_zcml)

	xmlconfig.include(context, file=library_zcml, package=conf_package)

	# Include zope.browserpage.meta.zcm for tales:expressiontype
	# before including the products
	xmlconfig.include(context, file="meta.zcml", package=zope.browserpage)
	
	# include plugins
	includePluginsDirective(context, PP_APP)
	includePluginsDirective(context, PP_APP_SITES)
	includePluginsDirective(context, PP_APP_PRODUCTS)
	
	return context
					
def main():
	arg_parser = argparse.ArgumentParser( description="Site operations" )
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	
	site_group = arg_parser.add_mutually_exclusive_group()
	
	site_group.add_argument('--list',
							dest='list',
							action='store_true',
							default=False,
							help="List all sites")	

	site_group.add_argument('--remove',
							 dest='remove',
							 help="remove a site")

	site_group.add_argument('--info',
							 dest='info',
							 help="print site info")
	
	env_dir = os.getenv( 'DATASERVER_DIR' )
	args = arg_parser.parse_args()
	if args.list:
		run_with_dataserver(environment_dir=env_dir,
							function=lambda: list_sites())
	elif args.remove:
		context = create_context(env_dir)
		conf_packages = (conf_package,)
		run_with_dataserver(environment_dir=env_dir,
							xmlconfig_packages=conf_packages,
							context=context,
							minimal_ds=True,
							verbose=args.verbose,
							function=lambda: remove_site(args.remove, args.verbose))
	elif args.info:
		context = create_context(env_dir)
		conf_packages = (conf_package,)
		run_with_dataserver(environment_dir=env_dir,
							xmlconfig_packages=conf_packages,
							context=context,
							minimal_ds=True,
							verbose=args.verbose,
							function=lambda: info_site(args.info))
		
	sys.exit( 0 )

if __name__ == '__main__':
	main()
