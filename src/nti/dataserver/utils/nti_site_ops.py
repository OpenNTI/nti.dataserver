#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse
from collections import Mapping

from zope import component

from zope.component.hooks import site as current_site

from zope.traversing.interfaces import IEtcNamespace

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import create_context

from nti.site.hostpolicy import get_all_host_sites

conf_package = 'nti.appserver'

def list_sites():
	for site in get_all_host_sites():
		name = site.__name__
		print("Site:", name)
		for k, v in site.items():
			print("\t", k, v)

def remove_sites(names=(), verbose=True, library=True):
	if library:
		try:
			from nti.contentlibrary.interfaces import IContentPackageLibrary
			pack_lib = component.queryUtility(IContentPackageLibrary)
			getattr(pack_lib, 'contentPackages', None)
		except ImportError:
			logger.warn("Cannot load library")
	sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
	for name in names or ():
		del sites_folder[name]
		if verbose:
			print('Site ' + name + ' removed')

def info_site(name):

	def _print(key, value, tabs=1):
		s = '\t' * tabs
		print(s, key, value)
		if isinstance(value, Mapping):
			for k, v  in value.items():
				_print(k, v, tabs + 1)

	sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
	local_site = sites_folder[name]
	with current_site(local_site):
		manager = local_site.getSiteManager()
		print("Site:", name)
		print("\tManager:", manager.__name__, manager)
		for key, value in manager.items():
			_print(key, value, 2)

def main():
	arg_parser = argparse.ArgumentParser(description="Site operations")
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
							 nargs="+",
							 help="remove sites")

	site_group.add_argument('--info',
							 dest='info',
							 help="print site info")

	env_dir = os.getenv('DATASERVER_DIR')
	args = arg_parser.parse_args()
	if args.list:
		context = create_context(env_dir, with_library=True)
		conf_packages = (conf_package,)
		run_with_dataserver(environment_dir=env_dir,
							xmlconfig_packages=conf_packages,
							context=context,
							minimal_ds=True,
							function=lambda: list_sites())
	elif args.remove:
		context = create_context(env_dir, with_library=True)
		conf_packages = (conf_package,)
		run_with_dataserver(environment_dir=env_dir,
							xmlconfig_packages=conf_packages,
							context=context,
							minimal_ds=True,
							verbose=args.verbose,
							function=lambda: remove_sites(args.remove, args.verbose))
	elif args.info:
		context = create_context(env_dir, with_library=True)
		conf_packages = (conf_package,)
		run_with_dataserver(environment_dir=env_dir,
							xmlconfig_packages=conf_packages,
							context=context,
							minimal_ds=True,
							verbose=args.verbose,
							function=lambda: info_site(args.info))

	sys.exit(0)

if __name__ == '__main__':
	main()
